import sys,collections,xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot(); target=sys.argv[2]; depth=int(sys.argv[3]) if len(sys.argv)>3 else 6
ids={}
def reg(e):
    if e.get('id'): ids[e.get('id')]=e
    for c in e: reg(c)
reg(root)
def R(e): return ids.get(e.get('ref'),e) if e.get('ref') else e
c=collections.Counter(); n=0
for row in root.iter('row'):
    th=bt=None
    for ch in row:
        if ch.tag=='thread': th=R(ch)
        if ch.tag in('backtrace','tagged-backtrace'): bt=R(ch)
    if th is None or bt is None or 'Main Thread' not in th.get('fmt',''): continue
    names=[R(f).get('name','?') for f in bt.iter('frame')]
    idx=[i for i,x in enumerate(names) if target in x]
    if not idx: continue
    n+=1; i=idx[-1]
    seen=set()
    for x in names[max(0,i-depth):i]:
        if x not in seen: seen.add(x); c[x]+=1
print("samples",n)
for k,v in c.most_common(45): print(v,k[:170])
