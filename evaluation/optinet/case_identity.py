"""Case file bindings stored in the dataset's shared identity index."""
from functools import lru_cache
from pathlib import Path
import json

@lru_cache(maxsize=4)
def _identity_index(filename, modified_ns):
    records = {}
    with Path(filename).open(encoding="utf-8-sig") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                key = row["case_dir"]
                if key in records:
                    raise ValueError("Duplicate case identity: " + key)
                records[key] = row
    return records

def load_identity(folder):
    folder = Path(folder).resolve()
    for parent in (folder, *folder.parents):
        if parent.name == "dataset":
            index = parent / "_meta/catalog/case_identity.jsonl"
            if index.is_file():
                key = "dataset/" + folder.relative_to(parent).as_posix()
                records = _identity_index(str(index), index.stat().st_mtime_ns)
                if key not in records:
                    raise ValueError("Case identity is missing: " + key)
                return records[key]
    raise ValueError("Dataset identity index was not found")
