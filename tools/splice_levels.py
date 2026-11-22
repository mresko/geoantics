"""Replace the `const LEVELS=[...];` line in index.html with tools/levels.json.
Usage: python3 tools/splice_levels.py index.html tools/levels.json"""
import sys
html_path, json_path = sys.argv[1], sys.argv[2]
lines = open(html_path, encoding='utf-8').read().split('\n')
data = open(json_path, encoding='utf-8').read().strip()
idx = [i for i, l in enumerate(lines) if l.startswith('const LEVELS=')]
assert len(idx) == 1, 'expected exactly one LEVELS line'
lines[idx[0]] = 'const LEVELS=' + data + ';'
open(html_path, 'w', encoding='utf-8').write('\n'.join(lines))
print('spliced', json_path, 'into', html_path)
