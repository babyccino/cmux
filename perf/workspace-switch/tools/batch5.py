import os
os.chdir(os.path.expanduser('~/Code/cmux'))
p='Sources/OwnWindowFrameCapture.swift'
s=open(p).read()
old='''        for index in 0..<samples.count where samples[index] != previous[index] {
            if index % gridX < sidebarColumns { sideChanged += 1 } else { mainChanged += 1 }
        }'''
assert old in s
s=s.replace(old,'''        var minX = gridX, minY = gridY, maxX = -1, maxY = -1
        for index in 0..<samples.count where samples[index] != previous[index] {
            if index % gridX < sidebarColumns { sideChanged += 1 } else { mainChanged += 1 }
            let x = index % gridX, y = index / gridX
            minX = min(minX, x); maxX = max(maxX, x); minY = min(minY, y); maxY = max(maxY, y)
        }''')
old='''            format: "photon seq=%d dt=%.1f side=%.3f main=%.3f",'''
assert old in s
s=s.replace(old,'''            format: "photon seq=%d dt=%.1f side=%.3f main=%.3f box=%d,%d-%d,%d",''')
old='''            Double(mainChanged) / Double(mainTotal)
        ))'''
assert old in s
s=s.replace(old,'''            Double(mainChanged) / Double(mainTotal),
            minX, minY, maxX, maxY
        ))''')
open(p,'w').write(s)
print("batch5 applied")
