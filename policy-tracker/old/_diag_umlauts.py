import gzip, json, unicodedata, html
with gzip.open('data/raw/germany/bgbl1_2008-2015_2019-2022_combined.json.gz', 'rt', encoding='utf-8') as f:
    data = json.load(f)
titles = [d['title'] for d in (data if isinstance(data, list) else data.values())]
umlaut_titles = [t for t in titles if any(c in t for c in 'äöüÄÖÜß')]
print(f'Titles with proper umlaut codepoints: {len(umlaut_titles)} / {len(titles)}')
print()
print('Sample titles (raw repr):')
for t in titles[:8]:
    print(' ', repr(t))
print()
nfd_count = sum(1 for t in titles if unicodedata.normalize('NFC', t) != t)
print(f'Titles that change under NFC normalization: {nfd_count}')
entity_count = sum(1 for t in titles if html.unescape(t) != t)
print(f'Titles with HTML entities: {entity_count}')
if umlaut_titles:
    print()
    print('Sample umlaut titles:')
    for t in umlaut_titles[:5]:
        print(' ', repr(t))
