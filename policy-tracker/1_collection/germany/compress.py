# this compress.py only serves the compression of fetched data that are too large to push to github (100 mb max)
##originals are then gitignored and compressed version is pushed

import gzip
import shutil
from pathlib import Path

input_file = (
    Path(__file__).parents[2]
    / "data"
    / "raw"
    / "germany"
    / "bgbl1_2008-2015_20260409.json"
)
output_file = input_file.with_suffix(".json.gz")

with open(input_file, "rb") as f_in:
    with gzip.open(output_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print(f"Compressed: {output_file}")
