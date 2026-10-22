import sys,collections,xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot()
ids={}
def resolve(e):
    r=e.get('ref')
    if r is not None: return ids[r]
    if e.get('id') is not None: ids[e.get('id')]=e
    for c in e: resolve(c)
    return e
incl=collections.Counter(); selfc=collections.Counter(); total=0
for row in root.iter('row'):
    th=None;bt=None
    for c in row:
        c2=resolve(c)
        if c.tag=='thread': th=c2
        if c.tag in ('backtrace','tagged-backtrace'): bt=c2
    if th is None or bt is None: continue
    name=th.get('fmt','')
    if 'Main Thread' not in name and 'main' not in name.lower(): continue
    frames=[]
    for f in bt.iter('frame'):
        f2=ids.get(f.get('ref')) if f.get('ref') else f
        if f2 is not None and f2.get('id'): ids[f2.get('id')]=f2
        frames.append(f2.get('name','?') if f2 is not None else '?')
    total+=1
    if frames: selfc[frames[0]]+=1
    for n in set(frames): incl[n]+=1
print("main-thread samples (1ms):",total)
print("-- top self"); [print(v,k[:150]) for k,v in selfc.most_common(15)]
print("-- top inclusive"); [print(v,k[:150]) for k,v in incl.most_common(int(sys.argv[2]) if len(sys.argv)>2 else 60)]
