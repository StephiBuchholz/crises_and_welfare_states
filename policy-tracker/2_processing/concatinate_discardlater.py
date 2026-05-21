import json
import gzip

PROJECT_ROOT = _find_root()

INPUT_FILE_1    = PROJECT_ROOT / "data/raw/germany/bgbl1_2019-2022_20260408.json"
INPUT_FILE_2    = PROJECT_ROOT / "data/raw/germany/bgbl1_2008-2015_20260409.json.gz"
OUTPUT_DIR    = PROJECT_ROOT / "data/raw/germany"


with open(INPUT_FILE_1, "r", encoding="utf-8") as f:
    data_a = json.load(f)

with gzip.open(INPUT_FILE_2, "rt", encoding="utf-8") as f:
    data_b = json.load(f)

combined = data_a + data_b

print(f"{len(data_a)} + {len(data_b)} = {len(combined)}")

with gzip.open(OUTPUT_DIR/"bgbl1_2008-2015_2019-2022_combined.json.gz", "wt", encoding="utf-8") as f:
    json.dump(combined, f, ensure_ascii=False, indent=2)where python
    