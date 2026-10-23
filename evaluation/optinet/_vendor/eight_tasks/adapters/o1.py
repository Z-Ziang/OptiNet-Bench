"""O1-S/O1-C English minimal-output grader; frozen source validator is the authority.

Only public_messages() is called to create Inspect model inputs. Private truth
and reference outputs are only accessed in scoring/replay, never in model input.
"""
from __future__ import annotations
from case_identity import load_identity
import argparse
from hashlib import sha256
import importlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'frozen/runtime'
sys.path.insert(0, str(RUNTIME))
TASKS = {'O1-S':'X2','O1-C':'X3'}
CLASSIFICATION_ABS_TOL = 1e-9


def readjson(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def sha(b):
    return sha256(b).hexdigest()


def _verify_runtime():
    manifest = RUNTIME / 'FILE_SHA256.json'
    if not manifest.exists():raise RuntimeError('Frozen runtime hash manifest missing')
    for rel,expected in readjson(manifest).items():
        path=(RUNTIME/rel).resolve()
        if not path.is_relative_to(RUNTIME.resolve()) or sha(path.read_bytes()) != expected:
            raise RuntimeError('Frozen runtime modified: '+rel)
_verify_runtime()


def manifest():
    with (ROOT/'catalog/case_index.jsonl').open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def resolve_case(relative):
    p=(ROOT/relative).resolve()
    if not p.is_relative_to((ROOT/'dataset').resolve()):raise ValueError('Case outside dataset')
    return p


def select_cases(task='all',topology='',scale='',limit_per_task=0):
    rows=[]; counts={}
    for r in manifest():
        if task!='all' and r['task']!=task:continue
        if topology and not (r['topology_folder']==topology or r['topology_folder'].startswith(topology+'_')):continue
        if scale and r['scale']!=scale:continue
        if limit_per_task and counts.get(r['task'],0)>=limit_per_task:continue
        rows.append(r);counts[r['task']]=counts.get(r['task'],0)+1
    if not rows:raise ValueError('No matching cases')
    return rows


def public_messages(row):
    folder=resolve_case(row['case_dir']);identity=load_identity(folder)
    messages=[]
    for role,name in [('system','system_prompt.txt'),('user','user_prompt.txt')]:
        rel='public/'+name;raw=(folder/rel).read_bytes()
        if sha(raw)!=identity['files'][rel]['sha256']:raise ValueError('Public input hash mismatch')
        messages.append({'role':role,'content':raw.decode('utf-8')})
    digest=sha(json.dumps(messages,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))
    if digest!=row['messages_sha256'] or digest!=identity['messages_sha256']:
        raise ValueError('Public message binding mismatch')
    return messages


def normalize_fence(text):
    stripped=text.strip()
    m=re.fullmatch(r'```(?:json)?\s*\r?\n(.*?)\r?\n```',stripped,re.I|re.S)
    return (m.group(1),True) if m else (stripped,False)


def _duplicate_key_reject(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON key: '+key)
        result[key]=value
    return result


def expand_for_frozen_validator(task, obj, fixed):
    """Validate the exact public minimal schema and reconstruct fixed source route(s).

    Returns a complete X2/X3 response (for the pinned validator) or raises ValueError.
    Paths come EXCLUSIVELY from private/fixed_paths.json; model cannot choose a route.
    """
    if not isinstance(obj,dict) or obj.get('decision') not in ('ACCEPT','REJECT'):
        raise ValueError('INVALID_DECISION_OR_OBJECT')
    paths=fixed['fixed_paths']
    if task=='O1-S':
        if set(obj)!= {'decision','slot_start'}:raise ValueError('UNEXPECTED_OR_MISSING_FIELDS')
        if len(paths)!=1:raise ValueError('INVALID_PRIVATE_PATH_COUNT')
        if obj['decision']=='REJECT':
            if obj['slot_start'] is not None:raise ValueError('REJECT_SLOT_MUST_BE_NULL')
            return {'decision':'REJECT','path_node_ids':[],'path_link_ids':[],'slot_start':None}
        n=obj['slot_start']
        if type(n) is not int or n<0 or n>=320:raise ValueError('INVALID_SLOT_START')
        path=paths[0]
        return {'decision':'ACCEPT','path_node_ids':list(path['path_node_ids']),
                'path_link_ids':list(path['path_link_ids']),'slot_start':n}
    if task!='O1-C':raise ValueError('UNKNOWN_TASK')
    if set(obj)!= {'decision','allocations'} or not isinstance(obj['allocations'],list):
        raise ValueError('UNEXPECTED_OR_MISSING_FIELDS')
    if obj['decision']=='REJECT':
        if obj['allocations']:raise ValueError('REJECT_ALLOCATIONS_MUST_BE_EMPTY')
        return {'decision':'REJECT','allocations':[]}
    by_id={p['request_id']:p for p in paths}
    if len(by_id)!=len(paths):raise ValueError('DUPLICATE_PRIVATE_REQUEST_IDS')
    submitted=obj['allocations']
    if len(submitted)!=len(by_id):raise ValueError('WRONG_ALLOCATION_COUNT')
    used=set();full=[]
    for item in submitted:
        if not isinstance(item,dict) or set(item)!= {'request_id','slot_start'}:
            raise ValueError('BAD_ALLOCATION_FIELDS')
        rid=item['request_id']
        if type(rid) is not str or rid not in by_id:raise ValueError('UNKNOWN_REQUEST')
        if rid in used:raise ValueError('DUPLICATE_REQUEST')
        used.add(rid)
        n=item['slot_start']
        if type(n) is not int or n<0 or n>=320:raise ValueError('INVALID_SLOT_START')
        path=by_id[rid]
        full.append({'request_id':rid,'path_node_ids':list(path['path_node_ids']),
                     'path_link_ids':list(path['path_link_ids']),'slot_start':n})
    return {'decision':'ACCEPT','allocations':full}


def classify(row,content,allow_single_fence=True):
    task=row['task']
    if task not in TASKS:raise ValueError('Unexpected task '+task)
    source_task=TASKS[task]
    folder=resolve_case(row['case_dir']);identity=load_identity(folder)
    for rel in ('private/root_case.json','private/private_truth.json','private/reference_output.json',
                'private/source_reference_output.json','private/fixed_paths.json'):
        if sha((folder/rel).read_bytes())!=identity['files'][rel]['sha256']:
            return {'category':'SCORING_ERROR','reason':'PRIVATE_FILE_HASH_MISMATCH','file':rel}
    vp=RUNTIME/'src/tasks'/source_task.lower()/'validator.py'
    if sha(vp.read_bytes())!=identity['validator_source_sha256']:
        return {'category':'SCORING_ERROR','reason':'FROZEN_VALIDATOR_HASH_MISMATCH'}
    root=readjson(folder/'private/root_case.json');truth=readjson(folder/'private/private_truth.json')
    fixed=readjson(folder/'private/fixed_paths.json')
    feasible=bool(truth['feasible' if source_task=='X2' else 'joint_feasible'])
    text,removed=normalize_fence(content) if allow_single_fence else (content,False)
    base={'truth_feasible':feasible,'single_outer_fence_removed':removed,
          'grading_version':'O1_MINIMAL_FIXED_PATH_V2',
          'derived_task':task,'source_task':source_task}
    try:
        obj=json.loads(text,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON')),
                       object_pairs_hook=_duplicate_key_reject)
    except (ValueError,TypeError):return {**base,'category':'MISSING','reason':'INVALID_JSON'}
    try:
        expanded=expand_for_frozen_validator(task,obj,fixed)
    except (ValueError,TypeError,KeyError) as e:
        return {**base,'category':'MISSING','reason':'OUTPUT_SCHEMA_ERROR','detail':str(e)}
    if obj['decision']=='REJECT' and feasible:
        return {**base,'category':'MISSING','reason':'INCORRECT_REJECT_NO_ALLOCATION'}
    validator=importlib.import_module('src.tasks.'+source_task.lower()+'.validator')
    v=getattr(validator,'validate_'+source_task.lower()+'_output')(root,truth,expanded)
    errors=[str(e).lower() for e in v.get('errors',[])]
    if any('truth inconsisten' in e or 'below stored optimum' in e for e in errors):
        return {**base,'category':'SCORING_ERROR','reason':'REFERENCE_OPTIMUM_CONFLICT','validator':v}
    if not v['valid']:return {**base,'category':'INFEASIBLE','validator':v}
    if obj['decision']=='ACCEPT':
        primary_gap=v.get('metrics',{}).get('hop_gap' if source_task=='X2' else 'delta_tso_gap')
        if primary_gap!=0:
            return {**base,'category':'SCORING_ERROR','reason':'FIXED_PATH_PRIMARY_GAP_NOT_ZERO','validator':v}
        frag_gap=v.get('metrics',{}).get('wufr_gap')
        if frag_gap is None:
            return {**base,'category':'SCORING_ERROR','reason':'FRAGMENTATION_NOT_SCORED','validator':v}
        category='SUBOPTIMAL' if frag_gap>CLASSIFICATION_ABS_TOL else 'CORRECT'
    else:category='CORRECT'
    return {**base,'category':category,'correct_reject':obj['decision']=='REJECT',
            'result_kind':'CERTIFIED_REJECT' if obj['decision']=='REJECT' else 'ALLOCATION',
            'validator':v}


def safe_classify(row,content,allow_single_fence=True):
    try:return classify(row,content,allow_single_fence)
    except Exception as e:return {'category':'SCORING_ERROR','reason':type(e).__name__,'message':str(e)}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--case-dir',required=True)
    p.add_argument('--answer',required=True)
    p.add_argument('--strict',action='store_true')
    a=p.parse_args()
    folder=Path(a.case_dir).resolve()
    row=next(r for r in manifest() if resolve_case(r['case_dir'])==folder)
    print(json.dumps(safe_classify(row,Path(a.answer).read_text(encoding='utf-8-sig'),not a.strict),indent=2,ensure_ascii=False))


def bind_dataset(root):
    global ROOT
    ROOT = Path(root).resolve()
