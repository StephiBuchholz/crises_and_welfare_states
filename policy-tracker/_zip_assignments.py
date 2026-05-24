import gzip, json
from pathlib import Path
p = Path('data/processed/germany/germany_2008-2015_2019-2022_berttopic_topic_assignments.json')
data = json.loads(p.read_text(encoding='utf-8'))
with gzip.open(str(p) + '.gz', 'wt', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False)
print('done')
