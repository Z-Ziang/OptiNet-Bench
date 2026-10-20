"""Q1 research pilot: exact, bounded simple-path search for ASE-only QoT RMSA.
No device-level QoT certification. Every proof refers only to MODEL_ID and ASSUMED guard rule.
All scores are computed by the copied X3 frozen implementation (see provenance).
"""
from __future__ import annotations
import collections, math, json, time
from .frozen_x3.wufr import network_wufr, build_reference_paths
MODEL_ID='ASE_ONLY_IDEAL_SPAN_COMPENSATION_V0.2_ASSUMED_GUARD'
H=6.62607015e-34; C=299792458.
PHYSICS={'wavelength_nm':1547.,'fiber_loss_db_per_km':0.2,'cd_ps_nm_km':17.,'span_max_km':80.,'amplifier_nf_db':5.,'signal_power_dbm':0.,'osnr_reference_hz':12.5e9,'margin_db':0.,'guard_slots':1,'model_id':MODEL_ID}
PROFILES={
 '200G_16QAM_32GBd':{'modulation':'16QAM','baud_gbd':32,'source_slots':3,'min_osnr_db':22.,'max_cd_ps_nm':10000.},
 '200G_8QAM_45GBd':{'modulation':'8QAM','baud_gbd':45,'source_slots':4,'min_osnr_db':16.,'max_cd_ps_nm':20000.},
 '200G_QPSK_60GBd':{'modulation':'QPSK','baud_gbd':60,'source_slots':6,'min_osnr_db':16.,'max_cd_ps_nm':50000.},
}
class Unknown(RuntimeError): pass

def width(case,profile):return PROFILES[profile]['source_slots']+case['physics']['guard_slots']
def qot(case,links,profile):
    p=case['physics']; length=sum(float(e['length_km']) for e in links)
    cd=length*p['cd_ps_nm_km'];ase=0.
    f=10**(p['amplifier_nf_db']/10);nu=C/(p['wavelength_nm']*1e-9)
    for edge in links:
        L=float(edge['length_km']);assert L>0
        n=math.ceil(L/p['span_max_km']);span=L/n
        gain=10**(p['fiber_loss_db_per_km']*span/10)
        ase+=n*f*H*nu*p['osnr_reference_hz']*(gain-1)
    osnr=10*math.log10(10**((p['signal_power_dbm']-30)/10)/ase)
    r=PROFILES[profile];return {'cd_ps_nm':cd,'osnr_db':osnr,'valid':cd<=r['max_cd_ps_nm']+1e-10 and osnr+1e-10>=r['min_osnr_db']+p['margin_db']}

def routes(case,src,dst,allowed,max_paths=10000):
    adjacency=collections.defaultdict(list)
    for e in case['directed_links']:
        if e['link_id'] in allowed:adjacency[e['source_node_id']].append(e)
    for x in adjacency.values():x.sort(key=lambda e:e['link_id'])
    found=0;stack=[(src,[src],[])]
    while stack:
        node,ns,es=stack.pop()
        if node==dst:
            found+=1
            if found>max_paths:raise Unknown('max_paths reached, no optimality claim')
            yield ns,es
        else:
            for e in reversed(adjacency[node]):
                v=e['destination_node_id']
                if v not in ns:stack.append((v,ns+[v],es+[e]))

def actions(case,req,max_paths=10000,max_actions=40000):
    spectra={r['link_id']:r['slot_availability'] for r in case['link_spectrum_states']}
    shortest=min(width(case,p) for p in PROFILES)
    allowed=set()
    for e,fs in spectra.items():
        run=0
        for f in fs:
            run=(run+1 if f else 0)
            if run>=shortest:allowed.add(e);break
    out=[]
    for ns,eds in routes(case,req['source_node_id'],req['destination_node_id'],allowed,max_paths):
        lids=[e['link_id'] for e in eds]
        common=[int(all(spectra[e][i] for e in lids)) for i in range(case['slot_count'])]
        for profile in PROFILES:
            phys=qot(case,eds,profile)
            if not phys['valid']:continue
            w=width(case,profile);run=0
            for end,x in enumerate(common):
                run=run+1 if x else 0
                if run>=w:
                    st=end-w+1
                    out.append({'request_id':req['request_id'],'path_node_ids':ns,'path_link_ids':lids,'transponder_profile_id':profile,'slot_start':st,'width':w,'cost':w*len(lids), 'masks':{e:((1<<w)-1)<<st for e in lids}})
                    if len(out)>max_actions:raise Unknown('max_actions reached')
    out.sort(key=lambda x:(x['cost'],tuple(x['path_link_ids']),x['transponder_profile_id'],x['slot_start']))
    return out

def evaluate(case,submission,reference_paths=None):
    err=[]
    if not isinstance(submission,dict):return {'valid':False,'errors':['not dict']}
    dec=submission.get('decision');al=submission.get('allocations')
    if dec=='REJECT':return {'valid':al==[],'errors':[] if al==[] else ['REJECT must have []'],'decision':'REJECT'}
    if dec!='ACCEPT':return {'valid':False,'errors':['invalid decision']}
    if not isinstance(al,list) or len(al)!=len(case['requests']):return {'valid':False,'errors':['wrong allocation count']}
    try:d={a['request_id']:a for a in al};ids=[r['request_id'] for r in case['requests']]
    except Exception:return {'valid':False,'errors':['malformed allocations']}
    if len(d)!=len(al) or set(d)!=set(ids):return {'valid':False,'errors':['missing / repeated request IDs']}
    emap={e['link_id']:e for e in case['directed_links']}
    sp={r['link_id']:list(r['slot_availability']) for r in case['link_spectrum_states']}
    cost=0;physical=[]
    for req in case['requests']:
        a=d[req['request_id']];profile=a.get('transponder_profile_id')
        ns=a.get('path_node_ids');links=a.get('path_link_ids');st=a.get('slot_start')
        if profile not in PROFILES or not isinstance(st,int) or isinstance(st,bool):err.append('profile/start invalid');continue
        if not isinstance(ns,list) or not isinstance(links,list) or not links or len(ns)!=len(links)+1:err.append('path shape invalid');continue
        if ns[0]!=req['source_node_id'] or ns[-1]!=req['destination_node_id'] or len(set(ns))!=len(ns):err.append('path endpoints or cycle');continue
        if any(lid not in emap or emap[lid]['source_node_id']!=u or emap[lid]['destination_node_id']!=v for lid,u,v in zip(links,ns,ns[1:])):err.append('directed path mismatch');continue
        w=width(case,profile)
        if st<0 or st+w>case['slot_count']:err.append('slot out of range');continue
        ph=qot(case,[emap[e] for e in links],profile);physical.append(ph)
        if not ph['valid']:err.append('QoT fail')
        for lid in links:
            for f in range(st,st+w):
                if sp[lid][f]!=1:err.append('spectrum overlap or occupied')
                sp[lid][f]=0
        cost+=w*len(links)
    if err:return {'valid':False,'errors':sorted(set(err))}
    q={int(k):float(v) for k,v in case['required_slots_probabilities'].items()}
    return {'valid':True,'decision':'ACCEPT','errors':[],'primary':cost,'secondary':network_wufr(case['nodes'],case['directed_links'],sp,q,reference_paths),'physics':physical}

def solve(case,max_paths=5000,max_actions=5000,max_nodes=150000,max_ties=2000):
    t0=time.monotonic();a={}
    for r in case['requests']:
        xs=actions(case,r,max_paths,max_actions);a[r['request_id']]=xs
        if not xs:return {'status':'INFEASIBLE_CERTIFIED','answer':{'decision':'REJECT','allocations':[]},'primary':None,'secondary':None,'nodes':0,'tied':0,'elapsed_s':round(time.monotonic()-t0,4),'action_counts':{k:len(v) for k,v in a.items()}}
    ordered=sorted(case['requests'],key=lambda r:(len(a[r['request_id']]),r['request_id']));mins=[a[r['request_id']][0]['cost'] for r in ordered]
    suffix=[0]*(len(mins)+1)
    for i in range(len(mins)-1,-1,-1):suffix[i]=mins[i]+suffix[i+1]
    taken={};picked={};best=float('inf');visits=0
    def dfs1(i,c):
        nonlocal best,visits
        visits+=1
        if visits>max_nodes:raise Unknown('primary budget exceeded')
        if c+suffix[i]>=best:return
        if i==len(ordered):best=c;return
        rid=ordered[i]['request_id']
        for x in a[rid]:
            if c+x['cost']+suffix[i+1]>=best:break
            if any(taken.get(e,0)&m for e,m in x['masks'].items()):continue
            for e,m in x['masks'].items():taken[e]=taken.get(e,0)^m
            dfs1(i+1,c+x['cost'])
            for e,m in x['masks'].items():taken[e]^=m
    dfs1(0,0)
    if best==float('inf'):return {'status':'INFEASIBLE_CERTIFIED','answer':{'decision':'REJECT','allocations':[]},'primary':None,'secondary':None,'nodes':visits,'tied':0,'elapsed_s':round(time.monotonic()-t0,4),'action_counts':{k:len(v) for k,v in a.items()}}
    refpaths=build_reference_paths(case['nodes'],case['directed_links']);tied=0;second=float('inf');output=None
    def dfs2(i,c):
        nonlocal second,output,tied,visits
        visits+=1
        if visits>max_nodes:raise Unknown('secondary budget exceeded')
        if c+suffix[i]>best:return
        if i==len(ordered):
            if c!=best:return
            tied+=1
            if tied>max_ties:raise Unknown('too many stage 1 optimal solutions, no secondary certification')
            answers=[{k:picked[r['request_id']][k] for k in ['request_id','path_node_ids','path_link_ids','transponder_profile_id','slot_start']} for r in case['requests']]
            y={'decision':'ACCEPT','allocations':answers}
            val=evaluate(case,y,refpaths)
            if not val['valid']:raise AssertionError(val)
            key=json.dumps(y,sort_keys=True)
            if val['secondary']<second-1e-12 or (abs(val['secondary']-second)<=1e-12 and (output is None or key<json.dumps(output,sort_keys=True))):second=val['secondary'];output=y
            return
        rid=ordered[i]['request_id']
        for x in a[rid]:
            if c+x['cost']+suffix[i+1]>best:break
            if any(taken.get(e,0)&m for e,m in x['masks'].items()):continue
            for e,m in x['masks'].items():taken[e]=taken.get(e,0)^m
            picked[rid]=x;dfs2(i+1,c+x['cost']);picked.pop(rid)
            for e,m in x['masks'].items():taken[e]^=m
    dfs2(0,0)
    return {'status':'EXACT_CERTIFIED','answer':output,'primary':best,'secondary':second,'nodes':visits,'tied':tied,'elapsed_s':round(time.monotonic()-t0,4),'action_counts':{k:len(v) for k,v in a.items()}}

def greedy(case,order='input'):
    req=list(case['requests']);aa={r['request_id']:actions(case,r) for r in req}
    if order=='fewest_actions':req.sort(key=lambda r:len(aa[r['request_id']]))
    elif order=='reverse':req.reverse()
    elif order=='largest_demand':req.sort(key=lambda r:-r['rate_gbps'])
    used={};sel={}
    for r in req:
        for x in aa[r['request_id']]:
            if any(used.get(e,0)&m for e,m in x['masks'].items()):continue
            sel[r['request_id']]=x
            for e,m in x['masks'].items():used[e]=used.get(e,0)|m
            break
        else:return {'decision':'REJECT','allocations':[]}
    return {'decision':'ACCEPT','allocations':[{k:sel[r['request_id']][k] for k in ('request_id','path_node_ids','path_link_ids','transponder_profile_id','slot_start')} for r in case['requests']]}
