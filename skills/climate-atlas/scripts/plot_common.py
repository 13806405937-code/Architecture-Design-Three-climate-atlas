# -*- coding: utf-8 -*-
"""气候分析图集 · 公共绘图工具

统一：白底 / 细灰网格 / 微软雅黑 / 参考 Ladybug Climate Analysis 的排版语言
"""
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_config as C

BASE = C.BASE
DATA = C.DATA
OUTROOT = C.OUTROOT

# 月份固定配色（12 色，用于太阳轨迹逐月日弧、月度图表）
MONTH_COLORS = ['#2E75B6', '#5B9BD5', '#548235', '#70AD47', '#A9D18E', '#C00000',
                '#FF0000', '#ED7D31', '#BF8F00', '#FFC000', '#7F6000', '#1F4E79']

# 场地范围（一切平面图的显示范围都从这里取，不再写字面量 0/180）
SX0, SY0 = float(C.SITE['xmin']), float(C.SITE['ymin'])
SX1, SY1 = float(C.SITE['xmax']), float(C.SITE['ymax'])
GRID_STEP = float(C.SITE.get('step', 2.0))
CELL_SIZE = float(C.SITE.get('cell', 1.0))


def site_axis(ax, n=3, fs=5.6):
    """按 site 配置设平面图范围与刻度"""
    ax.set_xlim(SX0, SX1)
    ax.set_ylim(SY0, SY1)
    ax.set_xticks(np.linspace(SX0, SX1, n))
    ax.set_yticks(np.linspace(SY0, SY1, n))
    ax.tick_params(labelsize=fs)


def site_grid(step=3.0, margin=None):
    """平面图上的采样网格（返回一维 xs, ys）"""
    m = GRID_STEP if margin is None else margin
    return np.arange(SX0 + m, SX1, step), np.arange(SY0 + m, SY1, step)

plt.rcParams.update({
    'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'Arial'],
    'axes.unicode_minus': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.edgecolor': '#AAAAAA',
    'axes.linewidth': 0.8,
    'axes.labelcolor': '#222222',
    'axes.grid': True,
    'grid.color': '#E6E6E6',
    'grid.linewidth': 0.7,
    'xtick.color': '#444444',
    'ytick.color': '#444444',
    'text.color': '#222222',
    'font.size': 10,
    'axes.titlesize': 12.5,
    'axes.labelsize': 10.5,
    'legend.fontsize': 9,
    'legend.frameon': False,
})

# 风速分级配色：低 → 高 = 深蓝 → 浅蓝 → 黄 → 橙 → 红（沿用 Ladybug 习惯）
SPEED_COLORS = ['#1F4E79', '#3A7CB8', '#8FC0E8', '#CFE3F5',
                '#F7E39B', '#EFA135', '#BE2F27']

C_TXT = '#222222'
C_SUB = '#6E6E6E'
C_GRID = '#DDDDDD'


def load_climate():
    with open(os.path.join(DATA, 'climate_data.json'), encoding='utf-8') as f:
        return json.load(f)


def load_extra(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------ 文案（可被 atlas.json 覆盖）
def L(key, default=''):
    """取 atlas.json 的 labels.<key>，没有则用默认值"""
    return (C.CFG.get('labels') or {}).get(key, default)


def meta():
    return load_climate()['meta']


def station_label():
    """气象站标签，如 'Shanghai CSWD WMO 583620'"""
    m = meta()
    bits = [m.get('city') or '', m.get('source') or '']
    if m.get('wmo'):
        bits.append('WMO %s' % m['wmo'])
    return ' '.join([b for b in bits if b]).strip()


def dateline(extra=''):
    s = '数据源：%s' % os.path.basename(meta()['epw'])
    if extra:
        s += '  |  ' + extra
    return s


def site_name_line():
    """地名 + 经纬度，如 '上海 31.40°N / 121.45°E'"""
    m = meta()
    nm = L('site_name', '') or (m.get('city') or '')
    return ('%s %.2f°N / %.2f°E' % (nm, m['latitude'], m['longitude'])).strip()


def source_line(extra='', geom=True):
    """页脚通栏：数据源 + 站点 + 引擎 + 几何 + 朝向"""
    m = meta()
    s = '数据源：%s' % os.path.basename(m['epw'])
    s += '  |  %.2f°N / %.2f°E' % (m['latitude'], m['longitude'])
    if m.get('engine'):
        s += '  |  引擎 %s' % m['engine']
    if geom:
        s += '  |  建筑几何：%s' % os.path.basename(C.MESH_PATH)
    s += '  |  朝向：模型 +X 方位角 %.1f°' % C.BRG_X
    if extra:
        s += '  |  ' + extra
    return s


def regime_note(cd):
    """按实测风向给一句季风描述（不写死城市）"""
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    wr = cd['windrose']

    def top(k):
        p = wr[k]['dir_pct']
        i = int(max(range(16), key=lambda j: p[j]))
        return dirs[i], p[i]

    ws_, wp = top('winter')
    ss_, sp = top('summer')
    return ['冬季 %s（%.1f%%） · 夏季 %s（%.1f%%）' % (ws_, wp, ss_, sp)]


def design_notes():
    """设计提示，由 atlas.json 的 labels.design_notes 提供（可为空）"""
    v = L('design_notes', [])
    return list(v) if isinstance(v, (list, tuple)) else []


def compact(lines):
    """去掉空行，避免 caption 出现大段空白"""
    return [x for x in lines if x not in (None, '')]


def viewpoint(key='sunpath', default=None):
    """观测点坐标，由 atlas.json 的 viewpoints.<key> 提供（[x, y, z]）"""
    v = (C.CFG.get('viewpoints') or {}).get(key)
    if not v:
        v = default or [(SX0 + SX1) / 2.0, (SY0 + SY1) / 2.0, 1.5]
    return float(v[0]), float(v[1]), float(v[2] if len(v) > 2 else 1.5)


def horizon_profile(hf, cell, px, py, pz, rmax=210.0, step=2.0, daz=2.0):
    """从 (px,py,pz) 看建筑，各真实方位角上的最大遮挡仰角

    hf/cell  : climate_engine.build_heightfield 的返回值
    返回     : (方位角数组 0–360, 最大仰角数组)
    """
    import climate_engine as E
    x0, y0 = float(C.SITE['xmin']), float(C.SITE['ymin'])
    x1, y1 = float(C.SITE['xmax']), float(C.SITE['ymax'])
    azis = np.arange(0.0, 360.0, daz)
    prof = np.zeros_like(azis)
    ds = np.arange(step, rmax, step)
    for i, a in enumerate(azis):
        th = math.radians(a)
        sx, sy = E.en_to_model(math.sin(th), math.cos(th))
        X = px + sx * ds
        Y = py + sy * ds
        ok = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
        if not ok.any():
            continue
        ii = np.rint((X[ok] - x0) / cell).astype(int).clip(0, hf.shape[1] - 1)
        jj = np.rint((Y[ok] - y0) / cell).astype(int).clip(0, hf.shape[0] - 1)
        h = hf[jj, ii]
        ang = np.degrees(np.arctan2(h - pz, ds[ok]))
        prof[i] = max(0.0, float(ang.max()))
    return azis, prof


def ensure(*parts):
    p = os.path.join(OUTROOT, *parts)
    os.makedirs(p, exist_ok=True)
    return p


def save(fig, folder, name, dpi=None):
    p = ensure(folder)
    fp = os.path.join(p, name)
    fig.savefig(fp, dpi=dpi or C.DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('saved:', os.path.join(folder, name))
    return fp


# ------------------------------------------------------------------ 极坐标玫瑰
def setup_polar(ax, dir_ticks=True, rmax=None):
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    if dir_ticks:
        th = np.arange(16) / 16 * 2 * np.pi
        ax.set_xticks(th)
        ax.set_xticklabels(['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'],
                           fontsize=7.2, color='#555555')
    if rmax:
        ax.set_ylim(0, rmax)
    ax.grid(color=C_GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color('#BBBBBB')
        s.set_linewidth(0.8)


def draw_windrose(ax, matrix, total_hours, calm_pct=None, rmax=None,
                  ring_step=5, width_frac=0.84, colors=None, label_fs=7.2,
                  show_rings=True):
    """matrix: (16,7) 小时数矩阵；径向 = 频率%"""
    colors = colors or SPEED_COLORS
    setup_polar(ax, rmax=None)
    n = matrix.shape[0]
    theta = np.arange(n) / n * 2 * np.pi
    freq = matrix / float(total_hours) * 100.0
    bot = np.zeros(n)
    w = np.radians(360.0 / n * width_frac)
    for k in range(matrix.shape[1]):
        ax.bar(theta, freq[:, k], width=w, bottom=bot,
               color=colors[k], edgecolor='white', linewidth=0.25, zorder=3)
        bot = bot + freq[:, k]
    if rmax is None:
        top = float(np.max(bot)) if bot.max() > 0 else 1.0
        rmax = math.ceil(top / ring_step) * ring_step
    ax.set_ylim(0, rmax)
    ticks = np.arange(ring_step, rmax + 1e-9, ring_step)
    ax.set_yticks(ticks)
    ax.set_yticklabels(['%d%%' % t for t in ticks], fontsize=6.8, color='#888888')
    ax.tick_params(axis='y', pad=-1)
    return rmax, bot


def wind_bottom_label(ax, txt, fs=6.8):
    ax.set_xlabel(txt, fontsize=fs, color=C_SUB, labelpad=-8)


def caption(fig, x, y, lines, fs=6.8, ha='left', color=C_SUB, lh=1.35):
    fig.text(x, y, '\n'.join(lines), ha=ha, va='top', fontsize=fs,
             color=color, linespacing=lh)


def speed_legend(fig, x, y, labels=None, colors=None, title='风速 m/s',
                 fs=6.8, box_h=0.016, box_w=0.012, gap=0.0015):
    labels = labels or ['<1', '1-2', '2-3', '3-4', '4-5', '5-6', '>6']
    colors = colors or SPEED_COLORS
    fig.text(x, y + 0.004, title, fontsize=fs + 0.4, color=C_TXT, ha='left', va='bottom')
    yy = y
    for lab, c in zip(labels, colors):
        fig.patches.append(plt.Rectangle((x, yy - box_h), box_w, box_h,
                                         transform=fig.transFigure, facecolor=c,
                                         edgecolor='white', linewidth=0.3))
        fig.text(x + box_w + 0.004, yy - box_h / 2, lab, fontsize=fs,
                 color=C_TXT, ha='left', va='center')
        yy -= (box_h + gap)


def speed_legend_h(fig, y, x0=0.30, labels=None, colors=None, title='风速 m/s',
                   fs=7.4, box_w=0.011, box_h=0.015, step=0.055):
    """横排风速图例"""
    labels = labels or ['<1', '1-2', '2-3', '3-4', '4-5', '5-6', '>6']
    colors = colors or SPEED_COLORS
    fig.text(x0 - 0.058, y + box_h / 2, title, fontsize=fs + 0.4,
             color=C_TXT, ha='left', va='center')
    x = x0
    for lab, c in zip(labels, colors):
        fig.patches.append(plt.Rectangle((x, y), box_w, box_h,
                                         transform=fig.transFigure, facecolor=c,
                                         edgecolor='white', linewidth=0.4))
        fig.text(x + box_w + 0.003, y + box_h / 2, lab, fontsize=fs,
                 color=C_TXT, ha='left', va='center')
        x += step


def header(fig, title, sub, y=0.985, fs_t=15.5, fs_s=9.2):
    fig.text(0.012, y, title, fontsize=fs_t, color=C_TXT,
             ha='left', va='top', weight='bold')
    fig.text(0.012, y - 0.030, sub, fontsize=fs_s, color=C_SUB,
             ha='left', va='top')


def footer(fig, txt, y=0.006, fs=6.6):
    fig.text(0.5, y, txt, fontsize=fs, color='#8A8A8A', ha='center', va='bottom')
