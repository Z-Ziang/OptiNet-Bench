"""Deterministic visible-answer parsing, independent of truth and scorer results."""
from __future__ import annotations

import hashlib
import json
import re

POLICY_VERSION = 'OPTINET_JSON_OUTPUT_V1'
FENCE = re.compile(r'```(?:json)?\s*\r?\n(.*?)\r?\n```', re.I | re.S)


def _integer(value):
    return type(value) is int


def _path(obj, *, cost=False):
    return (isinstance(obj, dict)
            and isinstance(obj.get('path_node_ids'), list)
            and isinstance(obj.get('path_link_ids'), list)
            and (not cost or _integer(obj.get('hop_count')))
            and ('total_length_km' not in obj or type(obj['total_length_km']) in (int, float)))


def matches_task_structure(task: str, obj) -> bool:
    """Recognize output fields and types, never feasibility or objective quality.

    The scientific validator remains authoritative after candidate selection.
    No private files, reference values or scorer calls are used here.
    """
    if not isinstance(obj, dict):
        return False
    if task == 'G1':
        field = {'EDGE_LIST':'edge_list', 'ADJACENCY_LIST':'adjacency_list',
                 'ADJACENCY_MATRIX':'adjacency_matrix'}.get(obj.get('representation_type'))
        return bool(field and isinstance(obj.get(field), dict if field == 'adjacency_list' else list)
                    and (field != 'adjacency_matrix' or isinstance(obj.get('nodes'), list)))
    if task == 'G2':
        return (set(obj) == {'is_valid', 'error_type'} and type(obj['is_valid']) is bool
                and (obj['error_type'] is None or isinstance(obj['error_type'], str)))
    if task == 'X1':
        return (_path(obj, cost=True)
                and set(obj) <= {'path_node_ids','path_link_ids','hop_count','total_length_km'})
    if task == 'G3':
        return (set(obj) == {'shortest_paths','has_shared_directed_link','shared_link_ids'}
                and type(obj['has_shared_directed_link']) is bool
                and isinstance(obj['shared_link_ids'], list)
                and isinstance(obj['shortest_paths'], list) and len(obj['shortest_paths']) == 2
                and all(_path(p, cost=True) and isinstance(p.get('pair_id'), str)
                        and set(p) <= {'pair_id','path_node_ids','path_link_ids','hop_count','total_length_km'}
                        for p in obj['shortest_paths']))
    if obj.get('decision') not in ('ACCEPT', 'REJECT'):
        return False
    if task == 'O1-S':
        return set(obj) == {'decision','slot_start'} and (obj['slot_start'] is None or _integer(obj['slot_start']))
    if task == 'X2':
        return (set(obj) == {'decision','path_node_ids','path_link_ids','slot_start'}
                and _path(obj) and (obj['slot_start'] is None or _integer(obj['slot_start'])))
    if task not in ('O1-C', 'X3', 'Q1') or not isinstance(obj.get('allocations'), list):
        return False
    if task != 'Q1' and set(obj) != {'decision','allocations'}:
        return False
    for item in obj['allocations']:
        if not isinstance(item, dict) or not isinstance(item.get('request_id'), str) or not _integer(item.get('slot_start')):
            return False
        fields = {'request_id','slot_start'}
        if task in ('X3', 'Q1'):
            if not _path(item):
                return False
            fields |= {'path_node_ids','path_link_ids'}
        if task == 'Q1':
            if not isinstance(item.get('transponder_profile_id'), str):
                return False
        elif set(item) != fields:
            return False
    return True


def _container_end(text, start):
    """Find a complete outer container without promoting nested/truncated JSON."""
    stack = []
    quoted = escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '{[':
            stack.append(char)
        elif char in '}]':
            if not stack or stack.pop() != ('{' if char == '}' else '['):
                return index + 1
            if not stack:
                return index + 1
    return None


def _invalid_constant(value):
    raise ValueError('Non-finite JSON constant: ' + value)


def _identity(text):
    """Preserve duplicate-key occurrences when deduplicating parsed JSON values."""
    class Pairs(list):
        pass
    def canonical(obj):
        if isinstance(obj, Pairs):
            values = tuple((key, canonical(value)) for key,value in obj)
            if len({key for key,value in obj}) != len(obj):
                return ('object_with_duplicate_keys', values)
            return ('object', tuple(sorted(values)))
        if isinstance(obj, list):
            return ('array', tuple(canonical(value) for value in obj))
        return (type(obj).__name__, repr(obj))
    return canonical(json.loads(text, object_pairs_hook=Pairs, parse_constant=_invalid_constant))


def prepare_relaxed_answer(task: str, answer: str) -> dict:
    """Select raw, whole-fence or unique task-shaped JSON before any scoring."""
    if not isinstance(answer, str):
        raise TypeError('Answer must be final visible response text')
    def result(method, status, text=None, start=None, end=None, count=0):
        return dict(policy_version=POLICY_VERSION, method=method, status=status,
                    candidate_count=count, text=text, start=start, end=end,
                    sha256=hashlib.sha256(text.encode('utf-8')).hexdigest() if text is not None else None)
    try:
        json.loads(answer)
    except (ValueError, TypeError, RecursionError):
        pass
    else:
        return result('raw', 'selected', answer, 0, len(answer))
    stripped = answer.strip()
    fence = FENCE.fullmatch(stripped)
    if fence:
        start = len(answer) - len(answer.lstrip()) + fence.start(1)
        return result('single_outer_fence', 'selected', fence.group(1), start, start + len(fence.group(1)))
    candidates = {}
    index = 0
    while index < len(answer):
        match = re.search(r'[\[{]', answer[index:])
        if not match:
            break
        start = index + match.start()
        end = _container_end(answer, start)
        if end is None:
            break
        text = answer[start:end]
        index = end
        try:
            obj = json.loads(text, parse_constant=_invalid_constant)
            if matches_task_structure(task, obj):
                candidates.setdefault(_identity(text), (text, start, end))
        except (ValueError, TypeError, RecursionError):
            continue
    if len(candidates) != 1:
        return result('none', 'ambiguous' if candidates else 'no_candidate', count=len(candidates))
    text, start, end = next(iter(candidates.values()))
    return result('json_extraction', 'selected', text, start, end, 1)
