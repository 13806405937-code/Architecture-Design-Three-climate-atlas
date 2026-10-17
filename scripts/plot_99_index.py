# -*- coding: utf-8 -*-
"""图集总览页（contact sheet）：六类图式的索引"""
import os

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

import plot_common as P

GROUPS = [
    ('00  总图版', ['00_气候分析总图版.png'], '#1A1A1A'),
    ('01  极坐标玫瑰族', ['01_风玫瑰_全年.png', '02_风玫瑰_逐月矩阵.png',
                    '03_风玫瑰_四季对比.png', '04_主导风向罗盘.png',
                    '05_太阳辐射玫瑰.png'], '#C1553B'),
    ('02  太阳轨迹族', ['01_太阳轨迹_全年.png', '02_太阳轨迹_观测点视角遮挡.png'], '#E09A2B'),
    ('03  逐时热图族', ['01_逐时热图矩阵_六参数.png'], '#4E8C8C'),
    ('04  月度图表族', ['01_月度图表_六联.png'], '#548235'),
    ('05  三维曲面族', ['01_温度钟点频次曲面.png'], '#7B5EA7'),
    ('06  建筑专题族', ['01_场地日照率分布.png', '02_阴影范围矩阵.png',
                   '03_立面太阳得热潜力.png'], '#2E75B6'),
    ('07  旧版成图（保留）', [], '#8A8A8A'),
]

items = []
for gname, files, col in GROUPS:
    for fn in files:
        fp = os.path.join(P.OUTROOT, gname.split('  ')[0] + '  ' + gname.split('  ')[1], fn) \
            if False else None
    # 用目录名找
for sub in sorted(os.listdir(P.OUTROOT)):
    d = os.path.join(P.OUTROOT, sub)
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if fn.lower().endswith('.png'):
            items.append((sub, fn, os.path.join(d, fn)))
# 总图版在最前
top = os.path.join(P.OUTROOT, '00_气候分析总图版.png')
if os.path.exists(top):
    items = [('★ 总图版', '00_气候分析总图版.png', top)] + \
            [it for it in items if it[2] != top]

COLS = 4
n = len(items)
rows = int(np.ceil(n / COLS))
fig = plt.figure(figsize=(COLS * 5.4, rows * 4.3 + 1.4))

for i, (sub, fn, fp) in enumerate(items):
    r, c = divmod(i, COLS)
    ax = fig.add_axes([0.012 + c * 0.2465, 0.055 + (rows - 1 - r) * 0.222,
                       0.234, 0.196])
    im = Image.open(fp)
    a = np.array(im)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    ax.imshow(a, aspect='auto')
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color('#D0D0D0')
        s.set_linewidth(0.8)
    ax.set_title('%s\n%s' % (sub, os.path.splitext(fn)[0]), fontsize=8.4,
                 color='#333333', pad=4, linespacing=1.5)

fig.text(0.012, 0.985, '%s · 总览' % P.L('title', '气候分析图集'), fontsize=17,
         weight='bold', color='#1A1A1A', va='top')
fig.text(0.012, 0.958,
         'Climate Analysis Atlas · Index  ·  %d 张成图  ·  %s' % (n, P.L('site_address', P.site_name_line())),
         fontsize=10, color='#666666', va='top')
fig.text(0.5, 0.012, P.source_line(), fontsize=7.4, color='#8A8A8A', ha='center')

p = os.path.join(P.OUTROOT, '99_图集总览.png')
fig.savefig(p, dpi=120, facecolor='white')
plt.close(fig)
print('saved', p, '  (%d items, %d rows)' % (n, rows))
