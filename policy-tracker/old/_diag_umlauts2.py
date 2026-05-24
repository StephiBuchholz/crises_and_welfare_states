import gzip, json, unicodedata
with gzip.open('data/raw/germany/bgbl1_2008-2015_2019-2022_combined.json.gz', 'rt', encoding='utf-8') as f:
    data = json.load(f)
titles = [d['title'] for d in (data if isinstance(data, list) else data.values())]

# Check for actual Unicode replacement character in data
replacement_char = '�'
repl_titles = [t for t in titles if replacement_char in t]
print(f"Titles containing U+FFFD (replacement char): {len(repl_titles)} / {len(titles)}")

# Check for x96 (Windows-1252 en dash decoded as Latin-1 C1 control)
x96_titles = [t for t in titles if '\x96' in t]
print(f"Titles containing \\x96 (cp1252 en dash mangled): {len(x96_titles)} / {len(titles)}")

# Check titles that lack proper umlauts -- what do they look like?
no_umlaut = [t for t in titles if not any(c in t for c in 'aouAOUss')]
print(f"\nTitles with NO umlaut-like chars at all: {len(no_umlaut)}")
for t in no_umlaut[:5]:
    print(' ', repr(t))

# Show sample of replacement-char titles
if repl_titles:
    print(f"\nSample replacement-char titles (first 5):")
    for t in repl_titles[:5]:
        # show hex of chars around the replacement char
        idx = t.index(replacement_char)
        snippet = t[max(0,idx-5):idx+6]
        print(f"  ...{repr(snippet)}... in: {repr(t[:60])}")
