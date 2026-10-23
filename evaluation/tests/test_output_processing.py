"""Output parsing and scoring regressions. No model API calls."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optinet.output_processing import prepare_relaxed_answer
from optinet import scoring
from optinet.data import inventory, reference


class OutputProcessingTests(unittest.TestCase):
    answer = '{"is_valid":true,"error_type":null}'

    def prepare(self, text):
        return prepare_relaxed_answer('G2', text)

    def test_raw_json_has_precedence(self):
        text = '{"comment":' + json.dumps(self.answer) + '}'
        result = self.prepare(text)
        self.assertEqual(result['method'], 'raw')
        self.assertEqual(result['text'], text)

    def test_whole_array_is_not_unwrapped(self):
        result = self.prepare('[' + self.answer + ']')
        self.assertEqual(result['method'], 'raw')

    def test_whole_fence_has_precedence_even_if_wrong_shape(self):
        text = '```json\n{"answer":' + self.answer + '}\n```'
        result = self.prepare(text)
        self.assertEqual(result['method'], 'single_outer_fence')

    def test_extracts_exact_substring_with_offsets(self):
        text = 'Here is the answer:\n' + self.answer + '\nDone.'
        result = self.prepare(text)
        self.assertEqual(result['method'], 'json_extraction')
        self.assertEqual(result['text'], self.answer)
        self.assertEqual(text[result['start']:result['end']], self.answer)

    def test_prose_with_a_fenced_answer(self):
        self.assertEqual(self.prepare('Answer:\n```json\n' + self.answer + '\n```')['text'], self.answer)

    def test_distinct_candidates_are_ambiguous(self):
        result = self.prepare(self.answer + '\nAlternative:\n{"is_valid":false,"error_type":null}')
        self.assertEqual(result['status'], 'ambiguous')
        self.assertIsNone(result['text'])
        self.assertEqual(result['candidate_count'], 2)

    def test_identical_values_deduplicate_without_rewriting_text(self):
        result = self.prepare('Example: ' + self.answer + '\nFinal: {"error_type": null, "is_valid": true}')
        self.assertEqual(result['candidate_count'], 1)
        self.assertEqual(result['text'], self.answer)

    def test_ignores_unrelated_objects(self):
        self.assertEqual(self.prepare('Metadata: {"note":"test"}\nAnswer: '+self.answer)['text'], self.answer)

    def test_missing_fields_are_not_repaired(self):
        self.assertEqual(self.prepare('Answer: {"is_valid":true}')['status'], 'no_candidate')

    def test_wrong_field_types_are_not_repaired(self):
        self.assertEqual(self.prepare('Answer: {"is_valid":"true","error_type":null}')['status'], 'no_candidate')

    def test_truncated_parent_is_not_salvaged(self):
        self.assertEqual(self.prepare('Answer: {"partial": ' + self.answer)['status'], 'no_candidate')

    def test_nested_objects_are_not_promoted(self):
        self.assertEqual(self.prepare('Answer: {"wrapper": ' + self.answer + '}')['status'], 'no_candidate')

    def test_braces_and_escaped_quotes_inside_strings(self):
        text = 'Metadata: {"note":"} and \\\" {"}\nAnswer: ' + self.answer
        self.assertEqual(self.prepare(text)['text'], self.answer)

    def test_scoring_does_not_select_the_better_candidate(self):
        class Grader:
            calls = []
            def grade(self, row, answer):
                self.calls.append(answer)
                return {'strict': {'category':'MISSING'}, 'relaxed': {'category':'MISSING'}}
        grader = Grader()
        with patch.dict(scoring._modules, {'G2': grader}):
            text = 'First: ' + self.answer + '\nSecond: {"is_valid":false,"error_type":null}'
            result = scoring.score_answer({'task':'G2'}, text)
        self.assertEqual(grader.calls, [text])
        self.assertEqual(result['relaxed']['reason'], 'AMBIGUOUS_JSON_CANDIDATES')

    def test_strict_grade_is_preserved_and_extracted_answer_is_scored(self):
        class Grader:
            def grade(self, row, answer):
                cat = 'CORRECT' if answer == OutputProcessingTests.answer else 'MISSING'
                return {'strict': {'category':cat}, 'relaxed': {'category':cat}}
        with patch.dict(scoring._modules, {'G2': Grader()}):
            result = scoring.score_answer({'task':'G2'}, 'Answer: ' + self.answer)
        self.assertEqual(result['strict']['category'], 'MISSING')
        self.assertEqual(result['relaxed']['category'], 'CORRECT')
        self.assertEqual(result['relaxed']['output_processing']['text'], self.answer)

    def test_scoring_error_is_never_hidden_by_extraction(self):
        class Grader:
            def grade(self, row, answer):
                return {'strict':{'category':'SCORING_ERROR'},'relaxed':{'category':'SCORING_ERROR','reason':'HASH_MISMATCH'}}
        with patch.dict(scoring._modules, {'G2': Grader()}):
            result = scoring.score_answer({'task':'G2'}, 'Answer: ' + self.answer)
        self.assertEqual(result['relaxed']['reason'], 'HASH_MISMATCH')

    def test_numeric_and_boolean_candidates_remain_distinct(self):
        text = 'A: {"decision":"ACCEPT","slot_start":1}\nB: {"decision":"ACCEPT","slot_start":true}'
        result = prepare_relaxed_answer('O1-S', text)
        self.assertEqual(result['candidate_count'], 1)
        self.assertEqual(json.loads(result['text'])['slot_start'], 1)

    def test_duplicate_keys_are_not_silently_changed_during_deduplication(self):
        result = self.prepare('A: '+self.answer+'\nB: {"is_valid":false,"is_valid":true,"error_type":null}')
        self.assertEqual(result['status'], 'ambiguous')

    def test_duplicate_key_order_is_preserved(self):
        a = '{"is_valid":false,"is_valid":true,"error_type":null}'
        b = '{"is_valid":true,"is_valid":false,"error_type":null}'
        self.assertEqual(self.prepare('A: '+a+'\nB: '+b)['status'],'ambiguous')

    def test_parseable_wrong_answer_is_not_replaced(self):
        text = '{"note":'+json.dumps(self.answer)+'}'
        class Grader:
            calls = []
            def grade(self, row, answer):
                self.calls.append(answer)
                return {'strict':{'category':'MISSING'},'relaxed':{'category':'MISSING'}}
        grader = Grader()
        with patch.dict(scoring._modules, {'G2':grader}):
            result = scoring.score_answer({'task':'G2'},text)
        self.assertEqual(grader.calls,[text])
        self.assertEqual(result['relaxed']['category'],'MISSING')


class ScientificIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[2]
        cls.rows = {}
        for row in inventory([str(root/'dataset')]):
            cls.rows.setdefault(row['task'],row)
            if len(cls.rows)==9:
                break

    def test_all_tasks_raw_fence_and_prose(self):
        for task,row in self.rows.items():
            answer = json.dumps(reference(row))
            raw = scoring.score_answer(row, answer)
            self.assertEqual(raw['strict']['category'], 'CORRECT', task)
            for method,text in [('single_outer_fence','```json\n'+answer+'\n```'),
                                ('json_extraction','Here is the answer:\n'+answer+'\nEnd.')]:
                with self.subTest(task=task,method=method):
                    result = scoring.score_answer(row,text)
                    self.assertEqual(result['strict']['category'],'MISSING')
                    self.assertEqual(result['relaxed']['category'],raw['strict']['category'])
                    self.assertEqual(result['relaxed']['output_processing']['method'],method)

    def test_infeasible_or_incorrect_candidate_is_still_scored(self):
        row = self.rows['G2']
        obj = reference(row)
        obj['is_valid'] = not obj['is_valid']
        answer = json.dumps(obj)
        direct = scoring.score_answer(row, answer)
        prose = scoring.score_answer(row,'Answer: '+answer)
        self.assertEqual(prose['relaxed']['category'],direct['strict']['category'])
        self.assertEqual(prose['relaxed']['output_processing']['method'],'json_extraction')
        self.assertNotEqual(prose['relaxed']['category'],'CORRECT')


if __name__ == '__main__':
    unittest.main()
