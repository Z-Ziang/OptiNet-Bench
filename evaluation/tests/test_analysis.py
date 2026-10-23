"""Regression checks for published-result aggregation conventions."""
from pathlib import Path
import sys
import unittest

EVALUATION = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVALUATION))
import analyze_results as analysis


def row(model, task, uid, success=True, scored=True, optimal=True, nodes=20):
    return dict(model=model, task=task, case_uid=uid, case_id=uid,
                node_count=str(nodes), scored=str(scored).lower(),
                decision_success=str(success).lower(),
                format_compliant='true', optimal_solution=str(optimal).lower(),
                outcome='correct' if success else 'incorrect')


class AggregationTests(unittest.TestCase):
    def test_pooled_and_equal_task_mean_differ_with_unequal_task_counts(self):
        rows=[row('example', task, task) for task in analysis.EIGHT_TASKS]
        rows += [row('example', 'G1', 'failed', success=False),
                 row('example', 'G1', 'service', success=False, scored=False)]
        result=analysis.overall_statistics(rows)[0]
        self.assertEqual(result['records'], 10)
        self.assertEqual(result['scored'], 9)
        self.assertEqual(result['success'], 8)
        self.assertAlmostEqual(result['pooled_e2e_pct'], 800/9)
        self.assertAlmostEqual(result['task_macro_e2e_pct'], 93.75)

    def test_macro_is_undefined_if_a_task_has_no_scored_response(self):
        rows=[row('example', task, task) for task in analysis.EIGHT_TASKS[1:]]
        result=analysis.overall_statistics(rows)[0]
        self.assertIsNone(result['task_macro_e2e_pct'])

    def test_scale_counts_x1_optima_over_scored_not_over_compliant(self):
        rows=[]
        for model in analysis.FRONTIER_MODELS:
            for task in analysis.GRAPH_TASKS:
                item=row(model, task, model+task, optimal=task!='X1')
                if task=='X1':
                    item['outcome']='feasible_suboptimal'
                    optimum=row(model,task,model+task+'optimal')
                    optimum['outcome']='optimal'
                    rows.append(optimum)
                    invalid=row(model,task,model+task+'invalid',success=False,optimal=False)
                    invalid['outcome']='format_invalid'
                    invalid['format_compliant']='false'
                    rows.append(invalid)
                rows.append(item)
                rows.append(row(model,task,model+task+'service',scored=False))
        result=analysis.scale_statistics(rows, bands=[('5-29',5,29)])[0]
        self.assertAlmostEqual(result['macro_accuracy_pct'],250/3)
        self.assertEqual(result['scored'],24)
        self.assertEqual(result['correct_or_optimal'],16)
        x1=next(cell for cell in result['cells'] if cell['task']=='X1')
        self.assertEqual((x1['correct_or_optimal'],x1['scored']),(1,3))

    def test_scale_reports_a_missing_required_cell(self):
        with self.assertRaises(ValueError):
            analysis.scale_statistics([], bands=[('5-29',5,29)])

    def test_topology_rates_average_graphs_before_size_strata(self):
        # One graph has repeated cases. Its accuracy contributes once to a
        # topology mean, while connectivity accuracy pools scored responses.
        rows=[];features={};catalog={}
        for i in range(12):
            graph='graph'+str(i)
            features[graph]=dict(graph_hash=graph,node_count='150',
                                average_shortest_path_hops=str(i+1),
                                global_edge_connectivity='1')
            for j in range(2 if i==0 else 1):
                uid=graph+'case'+str(j)
                catalog[uid]=dict(graph_hash=graph,node_count=150)
                rows.append(row('example','G3',uid,success=i<6,nodes=150))
        result=analysis.topology_statistics(rows,features,catalog,models=['example'])
        self.assertAlmostEqual(result['mean_hop']['high_minus_low_pp'],-100.0)
        self.assertEqual(result['mean_hop']['strata'][0]['low_topologies'],6)
        self.assertAlmostEqual(result['edge_connectivity']['summary'][0]['equal_band_accuracy_pct'],700/13)


class PublishedResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=analysis.read_results(EVALUATION.parent/'results/per_case_results.csv')

    def test_qwen_published_aggregates(self):
        results={r['model']:r for r in analysis.overall_statistics(self.rows)}
        for name,success,pooled,macro in [
            ('Qwen3-8B',601,32.6,29.3),
            ('Qwen3-8B (Non-Thinking)',196,10.6,9.3),
        ]:
            result=results[name]
            self.assertEqual((result['success'],result['scored']),(success,1843))
            self.assertEqual(round(result['pooled_e2e_pct'],1),pooled)
            self.assertEqual(round(result['task_macro_e2e_pct'],1),macro)

    def test_graph_scale_published_aggregates(self):
        bands={r['node_band']:r for r in analysis.scale_statistics(self.rows)}
        for band,expected in [('5-29',95.53165584415585),
                              ('301-400',51.838974993022966),
                              ('401-500',55.808714960701465)]:
            self.assertAlmostEqual(bands[band]['macro_accuracy_pct'],expected,places=10)

    def test_topology_published_aggregates(self):
        repo=EVALUATION.parent
        features,catalog=analysis.load_topology_inputs(
            repo/'dataset/_meta/catalog/topology_features.csv',
            repo/'dataset/_meta/catalog/case_index.jsonl')
        self.assertEqual(len(features),561)
        result=analysis.topology_statistics(self.rows,features,catalog)
        self.assertEqual((result['records'],result['distinct_topologies']),(928,196))
        self.assertAlmostEqual(result['mean_hop']['high_minus_low_pp'],-17.384785353535353,places=10)
        connectivity={r['connectivity']:r for r in result['edge_connectivity']['summary']}
        self.assertAlmostEqual(connectivity[1]['equal_band_accuracy_pct'],53.28714220808723,places=10)
        self.assertAlmostEqual(connectivity[3]['equal_band_accuracy_pct'],89.0625,places=10)


if __name__=='__main__':
    unittest.main()
