import sys,collections,xml.etree.ElementTree as ET
# usage: tree.py xml target maxdepth minsamples [skipregex]
import re
root=ET.parse(sys.argv[1]).getroot(); target=sys.argv[2]; maxd=int(sys.argv[3]); mins=int(sys.argv[4])
skip=re.compile(sys.argv[5]) if len(sys.argv)>5 else None
ids={}
def reg(e):
    if e.get('id'): ids[e.get('id')]=e
    for c in e: reg(c)
reg(root)
def R(e): return ids.get(e.get('ref'),e) if e.get('ref') else e
tree={}
def add(path):
    node=tree
    for p in path:
        ent=node.setdefault(p,[0,{}]); ent[0]+=1; node=ent[1]
for row in root.iter('row'):
    th=bt=None
    for ch in row:
        if ch.tag=='thread': th=R(ch)
        if ch.tag in('backtrace','tagged-backtrace'): bt=R(ch)
    if th is None or bt is None or 'Main Thread' not in th.get('fmt',''): continue
    names=[R(f).get('name','?') for f in bt.iter('frame')]
    idx=[i for i,x in enumerate(names) if target in x]
    if not idx: continue
    path=list(reversed(names[:idx[-1]]))
    if skip: path=[p for p in path if not skip.search(p)]
    add(path[:maxd])
def show(node,d):
    for k,(v,ch) in sorted(node.items(),key=lambda x:-x[1][0]):
        if v<mins: continue
        print('  '*d+f"{v} {k[:140]}")
        show(ch,d+1)
show(tree,0)
