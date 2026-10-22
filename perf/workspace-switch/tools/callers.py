import sys,re,collections,xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot(); target=sys.argv[2]; pat=re.compile(sys.argv[3] if len(sys.argv)>3 else r'Workspace|Terminal|Bonsplit|TabBar|Sidebar|Pane|Ghostty|Content|Portal|Split|cmux|Panel|Dock|Chief|Titlebar|Browser')
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
    if not any(target in x for x in names): continue
    n+=1
    i=next(i for i,x in enumerate(names) if target in x)
    seen=set()
    for x in names[i+1:]:
        if pat.search(x) and x not in seen:
            seen.add(x); c[x]+=1
print("samples",n)
for k,v in c.most_common(40): print(v,k[:170])
