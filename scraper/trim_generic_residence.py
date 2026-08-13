"""
trim_generic_residence.py

Removes R/RV/RW-prefixed files that aren't relevant to the SMC/PSWV/student
path, and rewrites manifest.json to match. Mirrors trim_student_visa.py.

Run this from the same folder as manifest.json:
    python trim_generic_residence.py
"""

import json
from pathlib import Path

MANIFEST_PATH = Path("manifest.json")

KEEP_R_CODES = {
    "R1",
    "R2", "R2.1", "R2.5", "R2.35", "R2.40", "R2.60",
    "R5", "R5.5", "R5.6", "R5.7", "R5.10", "R5.11", "R5.15", "R5.20", "R5.30",
    "R5.55", "R5.60", "R5.65", "R5.66", "R5.70", "R5.75", "R5.90", "R5.96",
    "R5.100", "R5.110", "R5.111", "R5.115",
    "R7", "R7.1", "R7.5", "R7.10", "R7.15",
}


def should_keep(section_code: str) -> bool:
    if not section_code.startswith("R"):
        return True  # leave SR, WD, U, A, V, WA untouched
    return section_code in KEEP_R_CODES


def main():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    pages = data.get("pages", [])

    kept, removed = [], []
    for entry in pages:
        if should_keep(entry["section_code"]):
            kept.append(entry)
        else:
            removed.append(entry)

    for entry in removed:
        file_path = Path(entry["file"].replace("\\", "/"))
        if file_path.exists():
            file_path.unlink()
            print(f"Deleted: {file_path}")
        else:
            print(f"Already missing, skipped: {file_path}")

    data["pages"] = kept
    MANIFEST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"\nKept {len(kept)} entries, removed {len(removed)} entries.")
    print(f"manifest.json updated -> {MANIFEST_PATH.resolve()}")


if __name__ == "__main__":
    main()