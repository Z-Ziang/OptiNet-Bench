# Dataset location and identity

Pass the local directory named `dataset` to `--dataset`, or put its relative path
in `config.json`. Its parent can be anywhere. The loader reads
`dataset/_meta/catalog/case_index.jsonl`; it does not scan arbitrary folders.

The code and expanded dataset are distributed together:
https://github.com/Z-Ziang/OptiNet-Bench

Install Git LFS before cloning. Run `git lfs pull` after cloning, then record
`git rev-parse HEAD`. Keep `evaluation/` and `dataset/` next to each other.
The large `_meta/request_id_normalization/source_provenance.jsonl` file uses
LFS; the rest are ordinary Git files. Run `verify-data` to check all original
bytes against the dataset manifest. No ZIP extraction or Hugging Face login
is required. This release preserves newline bytes with Git attributes.

All nine tasks use task/topology/Case/public-private directories. Directory
numbers are global within each task across topologies. The eight renamed tasks
retain their original scientific Case IDs and stable UIDs. The mapping is
`_meta/catalog/DIRECTORY_NAME_MAPPING.jsonl`. Historical provenance paths describe
source layouts; they are not runtime catalog paths. Q1 directories and payloads
remain unchanged, Q1_001 through Q1_2000.

Do not edit prompt/request IDs, scientific inputs, reference answers, proofs or
the frozen scoring contracts when renaming directories. Current catalogs,
metadata, identity bindings and SHA manifests must agree. Regenerate plans after
relocation or a dataset revision; join old model results by UID and message hash.

The dataset has 21,356 Cases, including 2,000 Q1 Cases: 600 LEGACY_V0.2 pure-200G
and 1,400 MIXED_V0.3 mixed-rate. Q1 has 1,950 EXACT_CERTIFIED and 50
INFEASIBLE_CERTIFIED records. Topologies and seeded snapshot variants are shared;
Case counts do not imply independent topology counts. See the dataset card for
construction, lineage, quotas and the public-reference caveat.
