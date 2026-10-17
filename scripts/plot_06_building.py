# -*- coding: utf-8 -*-
"""类型 6 · 建筑专题族（需要建筑几何）

- 场地日照时数分布（全年 / 夏季 / 冬季）—— 含建筑自遮挡
- 阴影范围矩阵（冬至 / 春分 / 夏至 × 9 / 12 / 15 时）
- 建筑各朝向立面可照时数与日照剖面
"""
import json
import math
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

from matplotlib.colors import ListedColormap

import plot_common as P
import climate_engine as E
import atlas_config as C

# 0 = 阴影, 1 = 受照
CMAP_SUN = ListedColormap(['#62707E', '#FBF2D6'])

CD = E.load_climate()
OBJS = E.load_building()
TRIS, OWNER = E.all_triangles(OBJS)

with open(C.MESH_PATH, encoding='utf-8') as f:
    _BM = json.load(f)
_SX, _SY = P.SX1 - P.SX0, P.SY1 - P.SY0
GROUND = [o for o in _BM['objects']
          if o.get('bb')[3] > _SX * 0.97 and o.get('bb')[4] > _SY * 0.97]
SITE_BB = [P.SX0, P.SY0, P.SX1, P.SY1]

ALT = np.array(CD['sunpath']['altitude_hourly'], dtype=float)
AZI = np.array(CD['sunpath']['azimuth_hourly'], dtype=float)
DIRS = E.sun_dirs(ALT, AZI)
MON = np.array(CD['hourly']['month'], dtype=int)
DAY = np.array(CD['hourly']['day'], dtype=int)
HOUR = np.array(CD['hourly']['hour'], dtype=int)

SUN = P.load_extra('sunhours_grid.json')
NORTH = E.true_north_in_model()


def draw_north(ax, x, y, L=17.0, fs=8.0, col='#333333'):
    """在模型坐标系里画指北针（模型 +Y 并非正北）"""
    ax.annotate('', xy=(x + NORTH[0] * L, y + NORTH[1] * L), xytext=(x, y),
                arrowprops=dict(arrowstyle='-|>', color=col, lw=1.5), zorder=8)
    ax.text(x + NORTH[0] * L * 1.26, y + NORTH[1] * L * 1.26, 'N',
            fontsize=fs + 1.5, color=col, ha='center', va='center', weight='bold', zorder=8)


def draw_building(ax, fc='#8C8C8C', ec='#4A4A4A', lw=0.5, alpha=1.0, z=4):
    for t in TRIS:
        ax.add_patch(MplPolygon(t[:, :2], closed=True, facecolor=fc,
                                edgecolor=ec, linewidth=lw, alpha=alpha, zorder=z))


def site_frame(ax, title, fs=10.5):
    ax.set_aspect('equal')
    ax.set_xlim(P.SX0 - 4, P.SX1 + 4)
    ax.set_ylim(P.SY0 - 4, P.SY1 + 4)
    ax.set_xticks(np.arange(P.SX0, P.SX1 + 1, max(50.0, round((P.SX1 - P.SX0) / 3.6 / 50) * 50)))
    ax.set_yticks(np.arange(P.SY0, P.SY1 + 1, max(50.0, round((P.SY1 - P.SY0) / 3.6 / 50) * 50)))
    ax.tick_params(labelsize=7.2)
    ax.set_xlabel('模型 X (m)', fontsize=7.6)
    ax.set_ylabel('模型 Y (m)', fontsize=7.6)
    ax.set_title(title, fontsize=fs, pad=5, color='#222222')
    ax.grid(color='#EDEDED', lw=0.6, zorder=0)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ 场地日照
def grid_from_points():
    xs = np.array(SUN['xs'], dtype=float)
    ys = np.array(SUN['ys'], dtype=float)
    co = np.array(SUN['coords'], dtype=float)
    step = SUN['step']
    ii = np.rint((co[:, 0] - xs[0]) / step).astype(int)
    jj = np.rint((co[:, 1] - ys[0]) / step).astype(int)
    out = {}
    for k in ('year', 'summer', 'winter', 'spring', 'autumn'):
        g = np.full((len(ys), len(xs)), np.nan)
        g[jj, ii] = np.array(SUN['hours_' + k], dtype=float)
        out[k] = g
    return xs, ys, out


def fig_site_sunhours():
    xs, ys, G = grid_from_points()
    X, Y = np.meshgrid(xs, ys)
    SH = SUN['season_hours']
    panels = [('全年  1/1 – 12/31', 'year', SH['year']),
              ('夏季  6–8 月', 'summer', SH['summer']),
              ('冬季  12–2 月', 'winter', SH['winter'])]
    fig = plt.figure(figsize=(17.2, 6.6))

    for i, (name, key, sh) in enumerate(panels):
        ax = fig.add_axes([0.030 + i * 0.245, 0.145, 0.205, 0.635])
        g = G[key] / float(sh) * 100.0
        m = ax.pcolormesh(X, Y, g, cmap='YlOrRd', vmin=0, vmax=100,
                          shading='nearest', zorder=2)
        draw_building(ax, fc='#7A7A7A', ec='#3D3D3D', lw=0.35, z=5)
        site_frame(ax, '%s        理论上限 %d h' % (name, sh))
        if i == 0:
            draw_north(ax, P.SX1 - 0.10 * _SX, P.SY0 + 0.05 * _SY, L=22, fs=8.5)
        cax = fig.add_axes([0.030 + i * 0.245 + 0.196, 0.175, 0.009, 0.575])
        cb = fig.colorbar(m, cax=cax)
        cb.set_label('日照率 (占可照时数 %)', fontsize=7.0)
        cb.ax.tick_params(labelsize=6.6)

        # 关键点位标注
        flat = np.nanargmax(g)
        jy, jx = np.unravel_index(flat, g.shape)
        ax.plot(xs[jx], ys[jy], marker='*', ms=11, mfc='#1A1A1A',
                mec='white', mew=0.8, zorder=7)
        ax.annotate('最高 %0.0f%%' % g[jy, jx], xy=(xs[jx], ys[jy]),
                    xytext=(xs[jx] - 4, ys[jy] - 26), fontsize=6.8, color='#1A1A1A',
                    ha='center',
                    arrowprops=dict(arrowstyle='->', color='#1A1A1A', lw=0.8))
        flat2 = np.nanargmin(g)
        jy2, jx2 = np.unravel_index(flat2, g.shape)
        ax.annotate('最低 %0.0f%%' % g[jy2, jx2], xy=(xs[jx2], ys[jy2]),
                    xytext=(xs[jx2], ys[jy2] + 20), fontsize=6.8, color='#7A2E1E',
                    ha='center',
                    arrowprops=dict(arrowstyle='->', color='#7A2E1E', lw=0.8))

    P.header(fig, '场地日照率分布（含建筑自遮挡）',
             'Site Sunlight Availability · 日照率 = 实际受照时数 ÷ 该时段太阳在地平线上的全部时数 · 网格 2 m', y=0.975)
    _yr = np.array(SUN['hours_year'], float) / float(SH['year']) * 100.0
    _sh = SUN['season_hours']
    P.caption(fig, 0.030, 0.085, P.compact([
        '算法：%d 个三角面光栅化为 %.0f m 高度场，逐网格点 × 逐小时做射线遮挡判定；'
        '场地网格 %.0f m，共 %d 点，剔除建筑投影内 %d 点。'
        % (len(TRIS), P.CELL_SIZE if hasattr(P, 'CELL_SIZE') else 1.0, SUN['step'],
           SUN['n_total_points'], SUN['on_building_count']),
        '模型朝向：+X 轴方位角 %.1f°、+Y 轴 %.1f°——模型 +Y 并非正北，图中指北针已按真实朝向绘制。'
        % (C.BRG_X, C.BRG_Y),
        '三张图统一为「日照率」口径可横向比较：全年日照率最低 %0.0f%%、中位数 %0.0f%%、最高 %0.0f%%；'
        '夏季可照 %d h、冬季可照 %d h。'
        % (np.nanmin(_yr), np.nanmedian(_yr), np.nanmax(_yr), _sh['summer'], _sh['winter']),
    ]), fs=7.0, color='#444444')
    P.footer(fig, P.source_line())
    return P.save(fig, '06_建筑专题', '01_场地日照率分布.png')


# ------------------------------------------------------------------ 阴影矩阵
def get_idx(mon, day, hour):
    sel = (MON == mon) & (DAY == day) & (HOUR == hour)
    w = np.where(sel)[0]
    return int(w[0]) if len(w) else None


def fig_shadow_matrix():
    hf, cell = E.build_heightfield(TRIS, cell=1.0, zmax=40.0)
    cases = [('冬至 12/22', 12, 22), ('春分 3/21', 3, 21), ('夏至 6/21', 6, 21)]
    times = [9, 12, 15]

    xs, ys = P.site_grid(3.0)
    GX, GY = np.meshgrid(xs, ys)
    PX = GX.ravel().astype(np.float32)
    PY = GY.ravel().astype(np.float32)
    PZ = np.full(PX.size, 0.05, dtype=np.float32)

    fig = plt.figure(figsize=(16.4, 15.2))
    for r, (cname, mm, dd) in enumerate(cases):
        for c, hh in enumerate(times):
            ax = fig.add_axes([0.045 + c * 0.318, 0.685 - r * 0.302, 0.245, 0.245])
            k = get_idx(mm, dd, hh)
            lit = E.sunlit(PX, PY, PZ, DIRS[k:k + 1], hf, cell=cell,
                           step=2.0, zmax=30.0)
            g = lit[:, 0].reshape(GX.shape).astype(float)
            gm = np.full(GX.shape, np.nan)
            gm[g > 0.5] = 1.0
            gm[g < 0.5] = 0.0
            ax.pcolormesh(GX, GY, gm, cmap=CMAP_SUN, vmin=0, vmax=1,
                          shading='nearest', zorder=1)
            draw_building(ax, fc='#4D4D4D', ec='#2A2A2A', lw=0.3, z=5)
            aspect = ALT[k]
            azi = AZI[k]
            sub = '%s  %02d:00   高度角 %.0f° / 方位角 %.0f°' % (cname, hh, aspect, azi)
            ax.set_aspect('equal')
            ax.set_xlim(P.SX0 - 2, P.SX1 + 2)
            ax.set_ylim(P.SY0 - 2, P.SY1 + 2)
            ax.set_facecolor('#F7F7F7')
            ax.set_xticks(np.linspace(P.SX0, P.SX1, 2))
            ax.set_yticks(np.linspace(P.SY0, P.SY1, 2))
            ax.tick_params(labelsize=6.4)
            ax.set_title(sub, fontsize=8.2, pad=4, color='#222222')
            ax.grid(color='#EDEDED', lw=0.5, zorder=0)
            ax.set_axisbelow(True)
            if c == 2 and r == 0:
                draw_north(ax, P.SX1 - 0.11 * _SX, P.SY0 + 0.07 * _SY, L=20, fs=8.0,
                           col='#FFFFFF')
            # 太阳方向小箭头
            sx, sy = DIRS[k, 0], DIRS[k, 1]
            _cx, _cy = P.SX1 - 0.045 * _SX, P.SY1 - 0.045 * _SY
            ax.annotate('', xy=(_cx + sx * 8, _cy + sy * 8), xytext=(_cx, _cy),
                        arrowprops=dict(arrowstyle='-|>', color='#E09A2B', lw=1.6),
                        zorder=9)
            ax.text(_cx, _cy - 0.065 * _SY, '太阳', fontsize=6.2, color='#B87A16',
                    ha='center', zorder=9)

    P.header(fig, '阴影范围矩阵 · 三个特征日 × 三个时刻',
             'Shadow Range Study · 深灰为建筑体块；地面浅米色 = 受太阳照射，蓝灰色 = 处于建筑阴影中', y=0.982)
    _k1 = get_idx(12, 22, 12)
    _k2 = get_idx(6, 21, 12)
    _hmax = float(hf.max())
    _a1, _a2 = (ALT[_k1], ALT[_k2]) if _k1 is not None and _k2 is not None else (0.0, 0.0)
    _l1 = _hmax / max(math.tan(math.radians(_a1)), 1e-6) if _a1 > 1 else 0.0
    P.caption(fig, 0.045, 0.052, P.compact([
        '朝向换算：模型 +X = 方位角 %.1f°，+Y = %.1f°，故图中指北针不指正上方。'
        % (C.BRG_X, C.BRG_Y),
        '冬至正午高度角 %0.0f°，最高体量 %.0f m 的阴影投距约 %0.0f m；夏至正午 %0.0f°，阴影最短、几乎落在自身投影内。'
        % (_a1, _hmax, _l1, _a2),
    ] + P.design_notes()), fs=7.2, color='#444444')
    P.footer(fig, P.source_line())
    return P.save(fig, '06_建筑专题', '02_阴影范围矩阵.png')


# ------------------------------------------------------------------ 立面日照
def fig_facade():
    """各朝向垂直面：全年可照时数（示意立面）"""
    up = DIRS[:, 2] > 0.04
    hf, cell = E.build_heightfield(TRIS, cell=1.0, zmax=40.0)

    fig = plt.figure(figsize=(15.0, 8.4))
    dirs8 = [('北 N', 0), ('东北 NE', 45), ('东 E', 90), ('东南 SE', 135),
             ('南 S', 180), ('西南 SW', 225), ('西 W', 270), ('西北 NW', 315)]

    tots = []
    for nm_, b_ in dirs8:
        af_ = math.radians(b_)
        ez_ = np.sin(np.radians(AZI)) * np.cos(np.radians(ALT))
        nz_ = np.cos(np.radians(AZI)) * np.cos(np.radians(ALT))
        tots.append(float((np.clip(ez_ * math.sin(af_) + nz_ * math.cos(af_), 0, None) * up).sum()))
    i_hi = int(np.argmax(tots))
    i_lo = int(np.argmin(tots))

    # 用「无限远」测点代表各朝向立面的日照可得性（不含自遮挡）
    for i, (nm, b) in enumerate(dirs8):
        r, c = divmod(i, 4)
        ax = fig.add_axes([0.045 + c * 0.242, 0.535 - r * 0.44, 0.185, 0.185],
                          projection='polar')
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        th = np.arange(16) * (2 * math.pi / 16)
        # 该朝向面在一年中每小时接收到的直射（以入射角为权重）
        af = math.radians(b)
        ez = np.sin(np.radians(AZI)) * np.cos(np.radians(ALT))
        nz = np.cos(np.radians(AZI)) * np.cos(np.radians(ALT))
        cosi = np.clip(ez * math.sin(af) + nz * math.cos(af), 0, None) * up
        per_month = np.array([cosi[MON == m].sum() for m in range(1, 13)])
        per_month = per_month / max(per_month.max(), 1e-9)
        ax.bar(np.arange(12) * (2 * math.pi / 12), per_month,
               width=np.radians(30 * 0.8), color='#EFA135', edgecolor='white',
               linewidth=0.4, zorder=3)
        ax.set_ylim(0, 1.15)
        ax.set_yticks([])
        ax.set_xticks(np.arange(12) * (2 * math.pi / 12))
        ax.set_xticklabels(['%d' % m for m in range(1, 13)], fontsize=6.0)
        ax.grid(color='#E6E6E6', lw=0.5)
        tot = cosi.sum()
        ax.set_title('%s   %.0f' % (nm, tot), fontsize=9.6, pad=6,
                     color='#222222')

    P.header(fig, '各朝向垂直面太阳得热潜力',
             'Solar Exposure by Facade Orientation · 角度加权后逐月分布（相对值）· 括号内为全年权重和')
    P.caption(fig, 0.045, 0.052, P.compact([
        '按入射角余弦加权的全年"晒太阳"强度，用于判断立面遮阳优先级与被动得热潜力。',
        '最高 %s（权重和 %.0f）、最低 %s（%.0f）——高值朝向冬季得热与夏季过热并存，'
        '宜做可调遮阳；低值朝向可减少遮阳投入，但需留意冬季失热。'
        % (dirs8[i_hi][0], tots[i_hi], dirs8[i_lo][0], tots[i_lo]),
    ] + P.design_notes()), fs=7.2, color='#444444')
    P.footer(fig, P.dateline())
    return P.save(fig, '06_建筑专题', '03_立面太阳得热潜力.png')


if __name__ == '__main__':
    fig_site_sunhours()
    fig_shadow_matrix()
    fig_facade()
    print('--- 类型 6 完成 ---')
