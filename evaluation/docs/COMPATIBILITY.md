# Compatibility

Use the entire evaluation directory with its optira package, task adapters,
frozen runtimes and contracts. The public interface is evaluate.py and the
Python API documented in INTERFACES.md. No source workspace is imported.

The enclosing project directory can be moved. Keep the dataset directory named
dataset and retain its _meta catalog; DATASET.md covers Hugging Face layouts.
Configuration dataset paths are relative to the config file. Plans bind absolute
dataset locations and message hashes: regenerate plans after moving data.

The eight tasks' directory names are TASK_NNN. Their source IDs/UIDs are unchanged;
current metadata and catalog paths follow the new directories. Provenance keeps
historical names. Q1 uses its existing Q1_NNN directories and unchanged payloads.

Q1 engine families are isolated packages and do not overwrite the eight-task src
package. Frozen scientific Python and grading tolerances remain unchanged by
directory normalization. O1 source task_type can still be X2/X3; dispatch using
the catalog/identity task. Supplemental validator identity bridges are retained.

Source REVIEW flags and source parser behavior remain authoritative. Frozen
historical schema IDs are not current package names. No translation or correction
of model prompts occurs during loading. See REVIEW.md for scientific limitations.
