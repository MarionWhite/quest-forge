import os, zipfile, json, re, sys
I = "/Users/suaz/Library/Application Support/PrismLauncher/instances/Quest Forge/minecraft/mods"
rows = []
for root, dirs, files in os.walk(I):
    for f in sorted(files):
        if not (f.endswith('.jar') or f.endswith('.zip')): continue
        p = os.path.join(root, f)
        rel = os.path.relpath(p, I)
        entry = {'file': rel, 'size': os.path.getsize(p)}
        try: z = zipfile.ZipFile(p)
        except Exception:
            entry['err'] = 'unreadable'; rows.append(entry); continue
        names = z.namelist()
        info = None
        for cand in ('mcmod.info', 'META-INF/mcmod.info'):
            if cand in names:
                try:
                    raw = z.read(cand).decode('utf-8', 'replace')
                    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', raw)
                    info = json.loads(raw)
                except Exception as e:
                    try:
                        info = json.loads(raw.replace('\n', ' '))
                    except Exception:
                        entry['raw_mcmod'] = raw[:600]
                break
        if info:
            lst = info.get('modList', info) if isinstance(info, dict) else info
            if isinstance(lst, list) and lst:
                m = lst[0]
                entry['modid'] = m.get('modid')
                entry['name'] = m.get('name')
                entry['version'] = m.get('version')
                entry['desc'] = (m.get('description') or '').strip()
                entry['authors'] = m.get('authorList') or m.get('authors')
                entry['url'] = m.get('url')
                if len(lst) > 1:
                    entry['extra'] = [x.get('name') for x in lst[1:]]
        rows.append(entry)
json.dump(rows, open('mods.json','w'), indent=1)
print(len(rows), 'archives')
for r in rows:
    print(f"{r['file'][:52]:54} | {str(r.get('name'))[:34]:36} | {str(r.get('version'))[:14]}")
