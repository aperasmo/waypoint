"""
trim_student_visa.py

Removes U-section files that aren't relevant to a Bachelor's/Master's/PhD
student visa path, and rewrites manifest.json to match.

Run this from the same folder as manifest.json:
    python trim_student_visa.py
"""

import json
from pathlib import Path

MANIFEST_PATH = Path("manifest.json")

KEEP_U_CODES = {
    "U1", "U2", "U2.1", "U3", "U3.1", "U3.5", "U3.7", "U3.10", "U3.20", "U3.40", "U3.45",
    "U4", "U4.10",
    "U5", "U5.1", "U5.20",
    "U6", "U6.1", "U6.15", "U6.25", "U6.30", "U6.40",
    "U7", "U7.5", "U7.20",
    "U8.25",
    "U13", "U13.1", "U13.5", "U13.15",
}


def should_keep(section_code: str) -> bool:
    if not section_code.startswith("U"):
        return True  # leave SR, WD, and anything else untouched
    return section_code in KEEP_U_CODES


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