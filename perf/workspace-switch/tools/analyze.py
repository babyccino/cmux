import re,sys,collections
base=sys.argv[1]
MINSEQ=int(__import__("os").environ.get("MINSEQ","1"))
thr=float(sys.argv[2]) if len(sys.argv)>2 else 0.01
ev=collections.defaultdict(dict)
for l in open(base+'.bg.log',errors='replace'):
    m=re.search(r'TMPSW seq=(\d+) (\S+).* dt=([-\d.]+)ms',l)
    if not m: continue
    s,e,dt=int(m.group(1)),m.group(2),float(m.group(3))
    if e=='cycle':
        a=re.search(r'eventAge=([\d.]+)',l)
        if a: ev[s]['eventAge']=float(a.group(1))
    ev[s].setdefault(e,dt)
ph=collections.defaultdict(list); keys={}; meta=[]
for l in open(base+'.photon.log',errors='replace'):
    m=re.search(r'photon seq=(\d+) dt=([-\d.]+) side=([\d.]+) main=([\d.]+)',l)
    if m: ph[int(m.group(1))].append((float(m.group(2)),float(m.group(3)),float(m.group(4))))
    elif 'autodrive key' in l:
        a=re.search(r'seq=(\d+) active=(\d) key=(\d)',l); keys[int(a.group(1))]=(a.group(2),a.group(3))
    else: meta.append(l.strip())
print('\n'.join(meta[:3]))
rows=[]
for s in sorted(ev):
    if s<=MINSEQ: continue
    fr=[f for f in ph.get(s,[]) if f[0]>=0 and f[0]<1000 and (f[1]>thr or f[2]>thr)]
    if not fr: rows.append((s,None,None,None,0,None,None)); continue
    first=fr[0][0]; last=fr[-1][0]
    mainfr=[f for f in fr if f[2]>thr]; sidefr=[f for f in fr if f[1]>thr]
    big=[f for f in fr if f[2]>0.2]
    rows.append((s,first,last,mainfr[-1][0] if mainfr else None,len(fr),sidefr[0][0] if sidefr else None,big[0][0] if big else None))
def st(v):
    v=sorted(x for x in v if x is not None)
    if not v: return 'n=0'
    return f"n={len(v):3d} p50={v[len(v)//2]:6.1f} p90={v[min(len(v)-1,int(len(v)*.9))]:6.1f} max={v[-1]:6.1f}"
print('first pixel change   ',st(r[1] for r in rows))
print('terminal swap (>20%) ',st(r[6] for r in rows))
print('sidebar first change ',st(r[5] for r in rows))
print('last terminal change ',st(r[3] for r in rows))
print('last change (settled)',st(r[2] for r in rows))
print('frames per switch    ',st(r[4] for r in rows))
print('no-change switches   ',sum(1 for r in rows if r[1] is None))
for k in ['eventAge','onChange','flushed','syncReveal.commitDone','portal.reveal']:
    v=[ev[s].get(k) for s in ev if s>1]
    if any(x is not None for x in v): print(f"{k:21s}",st(v))
inactive=[s for s,(a,k) in keys.items() if a!='1' or k!='1']
if inactive: print('switches with app inactive or window not key:',len(inactive))
