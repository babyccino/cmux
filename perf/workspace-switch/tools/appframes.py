import sys,re,collections,xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot(); target=sys.argv[2]
pat=re.compile(sys.argv[3] if len(sys.argv)>3 else r'(Workspace|Bonsplit|Terminal|Sidebar|ContentView|TabBar|Panel|Ghostty|Split|Pane|Chief|Titlebar|Portal|Window(?!Server))')
ids={}
def reg(e):
    if e.get('id'): ids[e.get('id')]=e
    for c in e: reg(c)
reg(root)
def R(e): return ids.get(e.get('ref'),e) if e.get('ref') else e
deep=collections.Counter(); outer=collections.Counter(); n=0
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
    inner=names[:i]
    app=[x for x in inner if pat.search(x) and not x.startswith('-[NS') and 'SwiftUI' not in x[:8]]
    deep[app[0] if app else '(no app frame) '+(inner[0] if inner else '')]+=1
    outer[app[-1] if app else '(none)']+=1
print("samples",n)
print("-- innermost app frame"); [print(v,k[:160]) for k,v in deep.most_common(30)]
print("-- outermost app frame"); [print(v,k[:160]) for k,v in outer.most_common(25)]
