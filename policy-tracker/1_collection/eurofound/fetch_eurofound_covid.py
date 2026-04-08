# 1 policy tracker prototype - covid eurofound policy tracker

# --------------------------------------------------------------------------------
# libraries

import pandas as pd
import json
from pathlib import Path

# --------------------------------------------------------------------------------

# url dataset eurofound covid

url = "https://static.eurofound.europa.eu/covid19db/data/covid19db.json"
outputpath = Path(
    "covid19db.json"
)  # puts the filename i save to in an object, path() enables certain features like .write_text()

# --------------------------------------------------------------------------------

# download json-formatted policy tracker from url

print(f"downloading from {url}...")
resp = requests.get(url, timeout=120)
resp.raise_for_status()  # gives out error message when failing or "200" when successful

eurofound_cov = resp.json()
print(f"downloaded {len(data)} policies.")

# store requested data in outputpath-doc as json-formatted file

outputpath.write_text(
    json.dumps(eurofound_cov, indent=2, ensure_ascii=False), encoding="utf-8"
)  # converts data back to json with 2-space indentation and ascii for readibility

print(f"saved as json")
