import subprocess, json, re, sys
pdf = sys.argv[1]; heads = json.load(open(sys.argv[2]))
n = int(re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout).group(1))
txt = [subprocess.run(['pdftotext', '-f', str(p), '-l', str(p), '-layout', pdf, '-'], capture_output=True, text=True).stdout for p in range(1, n + 1)]
out = {}
for h in heads:
    for p in range(3, n + 1):
        lines = [l.strip() for l in txt[p - 1].splitlines()]
        if any(l == h or l.startswith(h) and len(l) < len(h) + 3 for l in lines):
            out[h] = p; break
print(out, len(out), len(heads))
json.dump(out, open('toc_pages.json', 'w'), ensure_ascii=False)
