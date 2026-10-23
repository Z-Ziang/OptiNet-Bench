"""Reproduce aggregate statistics from the published results without model calls."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics

REPOSITORY = Path(__file__).resolve().parents[1]
EIGHT_TASKS = ('G1', 'G2', 'G3', 'X1', 'O1-S', 'O1-C', 'X2', 'X3')
GRAPH_TASKS = ('G1', 'G2', 'G3', 'X1')
FRONTIER_MODELS = ('Gemini 3.8 Flash', 'GPT-6.1 Sol', 'Claude Fable 5',
                   'DeepSeek-V4.1-Flash-1017')
NODE_BANDS = (('5-29', 5, 29), ('30-100', 30, 100), ('101-200', 101, 200),
              ('201-300', 201, 300), ('301-400', 301, 400), ('401-500', 401, 500))


def percentage(numerator, denominator):
    return 100.0 * numerator / denominator if denominator else None


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def read_results(path):
    rows = read_csv(path)
    required = {'model', 'case_uid', 'task', 'node_count', 'outcome', 'scored',
                'decision_success', 'optimal_solution'}
    if not rows or not required <= rows[0].keys():
        raise ValueError('Results must contain the published per-case fields.')
    seen = set()
    for row in rows:
        key = (row['model'], row['case_uid'])
        if key in seen:
            raise ValueError('Duplicate model/case record: ' + repr(key))
        seen.add(key)
        if row['scored'] not in ('true', 'false') or int(row['node_count']) <= 0:
            raise ValueError('Invalid scored indicator or node count: ' + repr(key))
        for field in ('decision_success', 'optimal_solution'):
            if row[field] not in ('true', 'false', ''):
                raise ValueError('Invalid ' + field + ': ' + repr(key))
    return rows


def overall_statistics(rows):
    """Eight-task E2E: pooled cases and equally weighted task percentages."""
    output = []
    for model in dict.fromkeys(row['model'] for row in rows):
        selected = [r for r in rows if r['model'] == model and r['task'] in EIGHT_TASKS]
        scored = [r for r in selected if r['scored'] == 'true']
        if not selected:
            continue
        success = sum(r['decision_success'] == 'true' for r in scored)
        tasks = []
        for task in EIGHT_TASKS:
            group = [r for r in scored if r['task'] == task]
            count = sum(r['decision_success'] == 'true' for r in group)
            tasks.append(dict(task=task, success=count, scored=len(group),
                              e2e_pct=percentage(count, len(group))))
        rates = [r['e2e_pct'] for r in tasks]
        output.append(dict(model=model, records=len(selected), scored=len(scored),
                           success=success, pooled_e2e_pct=percentage(success, len(scored)),
                           task_macro_e2e_pct=statistics.mean(rates) if None not in rates else None,
                           tasks=tasks))
    return output


def scale_statistics(rows, bands=NODE_BANDS, models=FRONTIER_MODELS):
    """Four graph tasks: model means within task, then task means within band."""
    output = []
    for label, lower, upper in bands:
        cells = []
        for task in GRAPH_TASKS:
            for model in models:
                group = [r for r in rows if r['model'] == model and r['task'] == task
                         and lower <= int(r['node_count']) <= upper]
                scored = [r for r in group if r['scored'] == 'true']
                if not scored:
                    raise ValueError('No scored cases for ' + repr((model, task, label)))
                correct = sum(r['optimal_solution'] == 'true' if task == 'X1'
                              else r['outcome'] == 'correct' for r in scored)
                cells.append(dict(model=model, task=task, records=len(group),
                                  scored=len(scored), correct_or_optimal=correct,
                                  accuracy_pct=percentage(correct, len(scored))))
        task_means = {task: statistics.mean(r['accuracy_pct'] for r in cells if r['task'] == task)
                      for task in GRAPH_TASKS}
        output.append(dict(node_band=label, macro_accuracy_pct=statistics.mean(task_means.values()),
                           task_means_pct=task_means, records=sum(r['records'] for r in cells),
                           scored=sum(r['scored'] for r in cells),
                           correct_or_optimal=sum(r['correct_or_optimal'] for r in cells), cells=cells))
    return output


def load_topology_inputs(features_path, catalog_path):
    features = {}
    for row in read_csv(features_path):
        graph = row['graph_hash']
        if graph in features:
            raise ValueError('Duplicate topology feature key: ' + graph)
        if int(row['node_count']) <= 1 or float(row['average_shortest_path_hops']) <= 0:
            raise ValueError('Invalid topology features: ' + graph)
        if int(row['global_edge_connectivity']) < 1:
            raise ValueError('Topology must be connected: ' + graph)
        features[graph] = row
    catalog = {}
    with Path(catalog_path).open(encoding='utf-8-sig') as handle:
        for line in handle:
            row = json.loads(line)
            if row['task'] == 'G3':
                if row['case_uid'] in catalog:
                    raise ValueError('Duplicate catalog case UID.')
                catalog[row['case_uid']] = row
    return features, catalog


def topology_statistics(rows, features, catalog, models=FRONTIER_MODELS):
    """G3 mean-hop and connectivity comparisons using physical graph properties."""
    selected = []
    for row in rows:
        if row['task'] != 'G3' or row['model'] not in models:
            continue
        case = catalog[row['case_uid']]
        feature = features[case['graph_hash']]
        nodes = int(row['node_count'])
        if nodes != int(case['node_count']) or nodes != int(feature['node_count']):
            raise ValueError('Topology node-count mismatch: ' + row['case_uid'])
        selected.append({**row, 'graph_hash': case['graph_hash'],
                         'mean_hops': float(feature['average_shortest_path_hops']),
                         'connectivity': int(feature['global_edge_connectivity'])})
    grouped = defaultdict(list)
    for row in selected:
        grouped[row['model'], row['graph_hash']].append(row)
    topologies = []
    omitted = 0
    for (model, graph), group in grouped.items():
        scored = [r for r in group if r['scored'] == 'true']
        if not scored:
            omitted += 1
            continue
        correct = sum(r['outcome'] == 'correct' for r in scored)
        topologies.append(dict(model=model, graph_hash=graph, node_count=int(group[0]['node_count']),
                               mean_hops=group[0]['mean_hops'],
                               accuracy_pct=percentage(correct, len(scored))))
    hop_strata, model_means = [], []
    for model in models:
        differences = []
        for label, lower, upper in NODE_BANDS:
            group = [r for r in topologies if r['model'] == model
                     and lower <= r['node_count'] <= upper]
            if not group:
                continue
            median = statistics.median(r['mean_hops'] for r in group)
            low = [r for r in group if r['mean_hops'] <= median]
            high = [r for r in group if r['mean_hops'] > median]
            eligible = min(len(low), len(high)) >= 5
            low_rate = statistics.mean(r['accuracy_pct'] for r in low) if low else None
            high_rate = statistics.mean(r['accuracy_pct'] for r in high) if high else None
            difference = high_rate - low_rate if low_rate is not None and high_rate is not None else None
            hop_strata.append(dict(model=model, node_band=label, median_mean_hops=median,
                                   low_topologies=len(low), high_topologies=len(high),
                                   low_accuracy_pct=low_rate, high_accuracy_pct=high_rate,
                                   high_minus_low_pp=difference, eligible=eligible))
            if eligible:
                differences.append(difference)
        model_means.append(dict(model=model, eligible_bands=len(differences),
                                high_minus_low_pp=statistics.mean(differences) if differences else None))
    means = [r['high_minus_low_pp'] for r in model_means]
    connectivity_strata, connectivity_summary = [], []
    for connectivity in (1, 2, 3):
        rates = []
        for label, lower, upper in NODE_BANDS[2:]:
            scored = [r for r in selected if r['scored'] == 'true'
                      and lower <= int(r['node_count']) <= upper and r['connectivity'] == connectivity]
            if not scored:
                continue
            correct = sum(r['outcome'] == 'correct' for r in scored)
            rate = percentage(correct, len(scored))
            rates.append(rate)
            connectivity_strata.append(dict(connectivity=connectivity, node_band=label,
                                            correct=correct, scored=len(scored), accuracy_pct=rate))
        connectivity_summary.append(dict(connectivity=connectivity, eligible_bands=len(rates),
                                          equal_band_accuracy_pct=statistics.mean(rates) if rates else None))
    return dict(records=len(selected), distinct_topologies=len({r['graph_hash'] for r in selected}),
                omitted_zero_scored_model_topologies=omitted,
                mean_hop=dict(high_minus_low_pp=statistics.mean(means) if means and None not in means else None,
                              per_model=model_means, strata=hop_strata),
                edge_connectivity=dict(summary=connectivity_summary, strata=connectivity_strata))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', choices=('overall', 'scale', 'topology', 'all'), default='all')
    parser.add_argument('--results', type=Path, default=REPOSITORY/'results/per_case_results.csv')
    parser.add_argument('--catalog', type=Path, default=REPOSITORY/'dataset/_meta/catalog/case_index.jsonl')
    parser.add_argument('--topology-features', type=Path,
                        default=REPOSITORY/'dataset/_meta/catalog/topology_features.csv')
    parser.add_argument('--out', type=Path, help='Optional JSON output file')
    args = parser.parse_args()
    rows = read_results(args.results)
    report = dict(percentage_unit='percent', difference_unit='percentage_points',
                  inputs={args.results.name: hashlib.sha256(args.results.read_bytes()).hexdigest()})
    if args.analysis in ('overall', 'all'):
        report['overall'] = overall_statistics(rows)
    if args.analysis in ('scale', 'all'):
        report['graph_scale'] = scale_statistics(rows)
    if args.analysis in ('topology', 'all'):
        features, catalog = load_topology_inputs(args.topology_features, args.catalog)
        report['topology'] = topology_statistics(rows, features, catalog)
        for path in (args.catalog, args.topology_features):
            report['inputs'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    rendered = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.out:
        args.out.write_text(rendered, encoding='utf-8')
    print(rendered, end='')


if __name__ == '__main__':
    main()
