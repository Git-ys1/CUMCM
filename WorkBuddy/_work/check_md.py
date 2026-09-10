import os

paths = [
    r'F:/AcademicHub/000资料相关/数模/26国赛/WorkBuddy/C题-求解编码规范与可复现性核对清单.md',
    r'F:/AcademicHub/000资料相关/数模/26国赛/WorkBuddy/README.md',
]

for p in paths:
    lines = open(p, encoding='utf-8').read().split('\n')
    blocks, cur, infence = [], [], False
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if s.startswith('```'):
            infence = not infence
            continue
        if infence:
            continue
        if s.startswith('|'):
            cur.append((i, l))
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    bad = 0
    for b in blocks:
        c = {}
        for i, l in b:
            c.setdefault(l.count('|'), []).append(i)
        if len(c) > 1:
            bad += 1
            print('  INCONSISTENT line', b[0][0], {k: v[:3] for k, v in c.items()})
    print(os.path.basename(p), '| blocks:', len(blocks), '| inconsistent:', bad)
