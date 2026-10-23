"""Offline checks of catalog identity and model-input isolation. No API calls."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from optinet.data import inside, inventory, public_messages
from optinet.cli import reject_secrets


class PublicBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='optinet_public_checks_')
        self.root=Path(self.temporary.name)/'arbitrary project name'
        self.data=self.root/'dataset'
        self.directory=self.data/'Q1/TOPOLOGY/Q1_001'
        (self.directory/'public').mkdir(parents=True)
        (self.directory/'private').mkdir()
        messages=[{'role':'system','content':'Return a JSON answer.'},{'role':'user','content':'Solve the public instance.'}]
        files={}
        for name,item in zip(('system_prompt.txt','user_prompt.txt'),messages):
            raw=item['content'].encode();(self.directory/'public'/name).write_bytes(raw)
            files['public/'+name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        (self.directory/'private/reference_output.json').write_text('PRIVATE_REFERENCE_SENTINEL',encoding='utf-8')
        self.row={'task':'Q1','case_uid':'2222222222222222222222222222222222222222222222222222222222222222','case_id':'Q1_0001',
            'case_dir':'dataset/Q1/TOPOLOGY/Q1_001','messages_sha256':hashlib.sha256(
                json.dumps(messages,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        self.catalog=self.data/'_meta/catalog/case_index.jsonl';self.catalog.parent.mkdir(parents=True)
        self.catalog.write_text(json.dumps(self.row)+'\n',encoding='utf-8')
        (self.catalog.parent/'case_identity.jsonl').write_text(json.dumps({**self.row,'files':files})+'\n',encoding='utf-8')

    def tearDown(self):
        self.temporary.cleanup()

    def test_private_content_is_not_model_input(self):
        row=next(inventory([str(self.data)]));messages=public_messages(row)
        self.assertEqual([m['role'] for m in messages],['system','user'])
        self.assertNotIn('PRIVATE_REFERENCE_SENTINEL',json.dumps(messages))

    def test_arbitrary_parent_location(self):
        self.assertEqual(next(inventory([str(self.root)]))['case_uid'],self.row['case_uid'])

    def test_tampered_prompt_is_rejected(self):
        (self.directory/'public/user_prompt.txt').write_text('tampered',encoding='utf-8')
        with self.assertRaises(ValueError):public_messages(next(inventory([str(self.data)])))

    def test_duplicate_case_is_rejected(self):
        with self.assertRaises(ValueError):list(inventory([str(self.data),str(self.data)]))

    def test_inventory_accepts_exact_canonical_case_id_filter(self):
        self.assertEqual([r['case_uid'] for r in inventory([str(self.data)], {'Q1_0001'})], [self.row['case_uid']])

    def test_inventory_task_filter(self):
        self.assertEqual(list(inventory([str(self.data)], wanted_tasks={'X2'})), [])

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):inside(self.data,'../outside.json')

    def test_nested_credential_is_rejected(self):
        with self.assertRaises(ValueError):reject_secrets({'nested':[{'api_key':'not-a-real-key'}]})

    def test_live_task_has_empty_target_and_public_inputs_only(self):
        import inspect_tasks
        row=next(inventory([str(self.data)]))
        with patch.object(inspect_tasks,'plan_rows',return_value=[row]):
            task=inspect_tasks.optinet_cases('unused.json',offline_reference=False)
        sample=task.dataset[0]
        self.assertEqual(sample.target,'')
        self.assertEqual(len(sample.input),2)
        self.assertNotIn('PRIVATE_REFERENCE_SENTINEL',str(sample.input))


if __name__=='__main__':unittest.main()
