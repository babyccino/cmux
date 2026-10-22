import re,sys,statistics
rows=[];cur=None
for l in open(sys.argv[1]):
    m=re.search(r'TMPSW (\S+).* dt=([\d.]+)ms',l)
    if not m: continue
    ev,dt=m.group(1),float(m.group(2))
    if ev=='cycle': cur={};rows.append(cur);continue
    if cur is not None and ev not in cur: cur[ev]=dt
for k in ['onChange','syncReveal.done','portal.hide','portal.reveal','syncReveal.commitDone']:
    v=sorted(r[k] for r in rows if k in r)
    if v: print(f"{k:24s} n={len(v):3d} p50={v[len(v)//2]:6.1f} p90={v[int(len(v)*.9)]:6.1f} min={v[0]:6.1f}")
