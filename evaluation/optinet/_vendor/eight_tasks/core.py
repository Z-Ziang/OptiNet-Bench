"""Portable data reader and adapters; never construct model inputs from private files."""
from __future__ import annotations
from case_identity import load_identity
import hashlib, importlib, json, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = ('G1','G2','G3','X1','O1-S','O1-C','X2','X3')
_modules = {}

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inside(root, relative):
    p = (Path(root)/relative).resolve()
    if not p.is_relative_to(Path(root).resolve()):
        raise ValueError('Path escapes dataset: '+str(relative))
    return p

def inventory(root):
    root = Path(root).resolve()
    with (root/'catalog/case_index.jsonl').open(encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                if row['task'] not in TASKS: raise ValueError('Unsupported task')
                if not inside(root,row['case_dir']).is_relative_to(root/'dataset'):
                    raise ValueError('Only default dataset cases are allowed')
                yield row

def checked_file(root, row, relative):
    folder = inside(root,row['case_dir'])
    identity = load_identity(folder)
    if identity['case_uid'] != row['case_uid'] or identity['task'] != row['task']:
        raise ValueError('Case identity mismatch')
    data = inside(folder,relative).read_bytes()
    expected = identity['files'][relative]
    if len(data)!=expected['bytes'] or digest(data)!=expected['sha256']:
        raise ValueError('File hash mismatch: '+relative)
    return data

def public_messages(root,row):
    messages = [{'role':role,'content':checked_file(root,row,'public/'+name).decode('utf-8')}
                for role,name in [('system','system_prompt.txt'),('user','user_prompt.txt')]]
    raw = json.dumps(messages,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    if digest(raw)!=row['messages_sha256']: raise ValueError('Message hash mismatch')
    return messages

def reference(root,row):
    name = 'reference_output.json'
    return json.loads(checked_file(root,row,'private/'+name))

def adapter(root,task):
    group = 'gx' if task in ('G1','G2','G3','X1') else 'o1' if task.startswith('O1-') else 'x'
    if group not in _modules: _modules[group] = importlib.import_module('adapters.'+group)
    mod = _modules[group]
    mod.bind_dataset(root)
    return mod

def score_answer(root,row,text):
    """Call frozen source classification twice, preserving strict and one-fence policies."""
    if not isinstance(text,str): raise TypeError('Answer must be final visible text')
    mod = adapter(root,row['task'])
    relaxed = mod.safe_classify(row,text,True)
    strict = mod.safe_classify(row,text,False)
    for result in (relaxed,strict):
        category = result.get('category','SCORING_ERROR')
        result['binary_label'] = ('CORRECT' if category=='CORRECT' else 'INCORRECT') if row['task'] in ('G1','G2','G3') and category!='SCORING_ERROR' else None
        result['is_certified_correct_reject'] = bool(result.get('correct_reject',False))
    return {'relaxed':relaxed,'strict':strict,'scoring_adapter_version':'OPTINET_EIGHT_TASKS_UNIFIED_POLICY_V1'}

def plan_rows(root,plan_path):
    plan = read_json(plan_path)
    if plan.get('schema')!='OPTINET_EIGHT_TASKS_PLAN_V1': raise ValueError('Wrong plan schema')
    wanted = plan['cases']; wanted_uids={r['case_uid'] for r in wanted}
    by_uid={r['case_uid']:r for r in inventory(root) if r['case_uid'] in wanted_uids}
    rows=[]
    for item in wanted:
        row=by_uid[item['case_uid']]
        for key in ('task','case_dir','messages_sha256'):
            if item[key]!=row[key]: raise ValueError('Plan/dataset mismatch: '+key)
        rows.append(row)
    if len({r['case_uid'] for r in rows})!=len(rows): raise ValueError('Duplicate plan UID')
    return rows
