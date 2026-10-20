# Public-release checklist

This is an engineering checklist, not certification by an external standards body.
The referenced guidance is used for documentation and reproducibility review:

- [Inspect tasks](https://inspect.aisi.org.uk/tasks.html): dataset, solver and scorer.
- [Hugging Face dataset cards](https://huggingface.co/docs/hub/datasets-cards):
  dataset description, construction, intended use, limitations and license metadata.
- [NeurIPS paper checklist](https://nips.cc/public/guides/PaperChecklist):
  reproducibility, experimental settings, source attribution and licensing.

| Requirement | Implementation or evidence |
|---|---|
| Clear installation and first run | README and pinned direct requirements |
| Nine task definitions and scoring | tasks/*/README.md and SCORING_PROTOCOL.md |
| Public/private input isolation | inspect_tasks.py and public_messages() |
| Code/data version binding | FILE_SHA256.json, dataset _meta/SHA256SUMS.json, run_identity.json |
| No account configuration | config.example.json placeholders; credentials through environment |
| Saved answers and detailed results | Inspect logs and export JSONL/CSV |
| Honest denominators and unresolved cases | SCORING_PROTOCOL.md and REVIEW.md |
| Topology and family dependence | Dataset card and DATASET.md |
| Naming preserves scientific payloads | Dataset DIRECTORY_NAMING_ACCEPTANCE.json |
| Reproducible execution evidence | Current ACCEPTANCE.json; local detailed logs are not shipped |
| Licensing and redistribution | Code: MIT; dataset: CC BY 4.0; see LICENSE_NOTICE.md |
| Actual publication URLs/revisions | Supply once the owner creates the GitHub/Hugging Face repositories |

The publication tree contains the CLI, Inspect task, shared adapters, frozen
validators/contracts, required source bindings/notices and current documentation.
Historical acceptance reports, production scripts, model outputs, logs, virtual
environments, caches and account files are outside this tree. FILE_SHA256.json
enumerates the shipped files; it excludes itself to avoid a self-referential hash.

Passing engineering checks does not grant third-party redistribution rights,
establish statistical independence, remove source REVIEW limitations or guarantee
that a remote model will return the same answer twice.
