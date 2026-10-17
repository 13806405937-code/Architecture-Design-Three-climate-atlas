# -*- coding: utf-8 -*-
"""类型 2 · 太阳轨迹族   |   类型 5 · 三维曲面族

太阳轨迹：等距投影（半径 = 90° − 太阳高度角），可叠加建筑遮挡轮廓
三维曲面：干球温度 × 钟点 → 出现频次
"""
import json
import math
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

import plot_common as P
import climate_engine as E

CD = E.load_climate()
OBJS = E.load_building()
TRIS, _ = E.all_triangles(OBJS)
HF, CELL = E.build_heightfield(TRIS, cell=1.0, zmax=40.0)

with open(os.path.join(P.DATA, 'epw_hourly.json'), encoding='utf-8') as f:
    R = json.load(f)
TA = np.array(R['ta'], dtype=float)
RH = np.array(R['rh'], dtype=float)
GHI = np.array(R['ghi'], dtype=float)
WS = np.array(R['wind_spd'], dtype=float)
HOURLY_H = np.array(R['hour'], dtype=int)
MONH = np.array(R['month'], dtype=int)
ALT_H = np.array(CD['sunpath']['altitude_hourly'], dtype=float)
AZI_H = np.array(CD['sunpath']['azimuth_hourly'], dtype=float)

ARCS = CD['sunpath']['arcs']
LAT = CD['sunpath']['latitude']
NORTH = E.true_north_in_model()

MONTH_COLORS = P.MONTH_COLORS


def horizon_profile(px, py, pz, rmax=210.0, step=2.0, daz=2.0):
    """从 (px,py,pz) 看建筑，各真实方位角上的最大遮挡仰角（转发 plot_common）"""
    return P.horizon_profile(HF, CELL, px, py, pz, rmax=rmax, step=step, daz=daz)


# ------------------------------------------------------------------ 类型 2
def fig_sunpath(hourly, show_shading=True, name='02_太阳轨迹_全年与遮挡.png', title_extra=''):
    fig = plt.figure(figsize=(11.6, 10.4))
    ax = fig.add_axes([0.075, 0.115, 0.655, 0.735], projection='polar')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)

    # 仰角圈
    for alt in (0, 15, 30, 45, 60, 75):
        r = 90 - alt
        tt = np.linspace(0, 2 * math.pi, 200)
        ax.plot(tt, np.full_like(tt, r), color='#E2E2E2', lw=0.7, zorder=1)
    ax.set_ylim(90, 0)
    ax.set_yticks([90 - a for a in (0, 15, 30, 45, 60, 75)])
    ax.set_yticklabels(['0°', '15°', '30°', '45°', '60°', '75°'],
                       fontsize=6.6, color='#999999')
    th16 = np.arange(16) / 16 * 2 * math.pi
    ax.set_xticks(th16)
    ax.set_xticklabels(['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'],
                       fontsize=7.0, color='#555555')
    ax.grid(color='#EFEFEF', lw=0.5)

    # 遮挡轮廓（可从小时数据标出被遮时点）
    if show_shading:
        azis, prof = horizon_profile(hourly[0], hourly[1], hourly[2])
        thp = np.radians(azis)
        rp = 90 - prof
        ax.plot(np.append(thp, thp[0]), np.append(rp, rp[0]), color='#4A4A4A',
                lw=1.8, zorder=6)
        ax.fill(np.append(thp, thp[0]), np.append(rp, rp[0]), color='#D8D8D8',
                alpha=0.55, zorder=5)

    # 逐月日弧
    for arc in ARCS:
        mo = arc['month']
        pts = [p for p in arc['points'] if p[1] > 0.0]
        if len(pts) < 2:
            continue
        th = np.radians([p[2] for p in pts])
        r = 90 - np.array([p[1] for p in pts])
        lw = 2.6 if mo in (6, 12) else 1.25
        al = 1.0 if mo in (6, 12) else 0.85
        ax.plot(th, r, '-', color=MONTH_COLORS[mo - 1], lw=lw, alpha=al, zorder=4)
        # 整点标记
        ax.plot(th[::2], r[::2], 'o', ms=1.9, color=MONTH_COLORS[mo - 1],
                alpha=al, zorder=4)

    # 关键日标注
    for mo, lab, col in ((6, '夏至', '#C00000'), (12, '冬至', '#1F4E79')):
        arc = [a for a in ARCS if a['month'] == mo][0]
        pts = [p for p in arc['points'] if p[1] > 0]
        noon = min(pts, key=lambda p: 90 - p[1])
        ax.annotate('%s 正午\n高度角 %.1f°' % (lab, noon[1]),
                    xy=(math.radians(noon[2]), 90 - noon[1]),
                    xytext=(math.radians(noon[2] + 22), 90 - noon[1] - 12),
                    fontsize=7.6, color=col, ha='center',
                    arrowprops=dict(arrowstyle='->', color=col, lw=0.9), zorder=8)

    # 图例：月份色环
    leg_x, leg_y = 0.775, 0.635
    fig.text(leg_x, leg_y + 0.050, '月份', fontsize=7.6, color=P.C_TXT)
    for i in range(12):
        cx = leg_x + (i % 3) * 0.070
        cy = leg_y - (i // 3) * 0.029
        fig.add_artist(plt.Line2D([cx, cx + 0.030], [cy, cy],
                                  transform=fig.transFigure,
                                  color=MONTH_COLORS[i], lw=2.4))
        fig.text(cx + 0.034, cy, '%d 月' % (i + 1), fontsize=7.0,
                 color='#333333', va='center', ha='left')

    P.caption(fig, leg_x - 0.012, leg_y - 0.140, [
        '%s' % title_extra,
        '等距投影：半径 = 90° − 高度角',
        '外圈 = 地平线，圆心 = 天顶',
        '每弧间隔 1 小时取点',
        '',
        '夏至昼长 14.1 h，正午 82°',
        '冬至昼长 10.2 h，正午 35°',
        '',
        '深灰轮廓 = 建筑遮挡线',
        '轮廓以上为可见天空，',
        '以下时段该点处于阴影。',
    ], fs=7.0, color='#444444')

    P.header(fig, '太阳轨迹图' + ('  ·  含建筑遮挡' if show_shading else ''),
             'Sun Path Diagram · %s · 等距投影 · 12 个月日弧' % P.site_name_line())
    P.footer(fig, P.source_line())
    return P.save(fig, '02_太阳轨迹', name)


def fig_sunpath_shading():
    vp = P.viewpoint('sunpath')
    return fig_sunpath(vp, True, '02_太阳轨迹_观测点视角遮挡.png',
                       title_extra='观测点：(%.0f, %.0f)' % (vp[0], vp[1]))


def fig_sunpath_dome():
    """太阳轨迹天穹图（等距投影全磁盘）

    把全年逐时太阳位置（方位角 × 高度角）聚到 5° 蜂窝格上，分别着色为
    ①该位置累计出现小时数 ②该位置平均干球温度 ③该位置平均太阳总辐射。
    色带形态即全年太阳在天空中的实际分布。
    """
    up = ALT_H > 0.0
    GS = 5.0
    ga = np.round(ALT_H[up] / GS) * GS
    gz = np.round((AZI_H[up] % 360.0) / GS) * GS
    key = (ga * 1000.0 + gz).astype(np.int64)
    uniq, inv = np.unique(key, return_inverse=True)
    g_th = np.radians((uniq % 1000).astype(float))
    g_r = 90.0 - (uniq // 1000).astype(float)
    cnt = np.bincount(inv).astype(float)
    m_ta = np.bincount(inv, weights=TA[up]) / np.maximum(cnt, 1.0)
    m_ghi = np.bincount(inv, weights=GHI[up]) / np.maximum(cnt, 1.0)

    panels = [('太阳轨迹位置 · 累计小时数', cnt, 'YlGnBu', 'h / 格', '%.0f'),
              ('该位置平均干球温度', m_ta, 'RdYlBu_r', '°C', '%.0f'),
              ('该位置平均太阳总辐射', m_ghi, 'YlOrRd', 'W/m²', '%.0f')]

    fig = plt.figure(figsize=(16.8, 7.9))
    for i, (title, V, cmap, unit, fmt) in enumerate(panels):
        ax = fig.add_axes([0.035 + i * 0.314, 0.205, 0.230, 0.588],
                          projection='polar')
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        sc = ax.scatter(g_th, g_r, c=V, cmap=cmap, s=17, marker='h',
                        edgecolors='none', zorder=3)
        # 参考年日弧（春分 / 夏至 / 冬至）
        for mo, col in ((3, '#2F2F2F'), (6, '#C00000'), (12, '#1F4E79')):
            arc = [a for a in ARCS if a['month'] == mo][0]
            pts = [p for p in arc['points'] if p[1] > 0]
            if len(pts) < 2:
                continue
            ax.plot(np.radians([p[2] for p in pts]),
                    90 - np.array([p[1] for p in pts]),
                    '-', color=col, lw=1.4, alpha=0.9, zorder=6)
        for alt in (15, 30, 45, 60, 75):
            tt = np.linspace(0, 2 * math.pi, 180)
            ax.plot(tt, np.full_like(tt, 90 - alt), color='#C8C8C8',
                    lw=0.55, zorder=2)
        ax.set_ylim(90, 0)
        ax.set_yticks([90 - a for a in (15, 30, 45, 60, 75)])
        ax.set_yticklabels(['15°', '30°', '45°', '60°', '75°'],
                           fontsize=6.0, color='#8A8A8A')
        ax.set_xticks(np.arange(16) / 16 * 2 * math.pi)
        ax.set_xticklabels(['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'],
                           fontsize=6.4, color='#555555')
        ax.grid(color='#DDDDDD', lw=0.45, zorder=1)
        ax.set_title(title, fontsize=10.0, color='#222222', pad=9)
        cax = fig.add_axes([0.035 + i * 0.314 + 0.232, 0.540, 0.011, 0.253])
        cb = fig.colorbar(sc, cax=cax)
        cb.ax.tick_params(labelsize=6.4, length=2)
        tk = np.linspace(V.min(), V.max(), 5)
        cb.set_ticks(tk)
        cb.ax.set_yticklabels([fmt % v for v in tk])
        cb.set_label(unit, fontsize=6.8, labelpad=2)

    P.caption(fig, 0.035, 0.045, [
        '读图：三张图共用同一套天穹网格（径向 = 90° − 高度角，方位角自北顺时针），每个蜂窝格 = 太阳停留过的 5°×5° 天区，只在与太阳实际出现过的位置着色，色带形态即全年太阳轨迹包络。',
        '左：轨迹停留小时数——低仰角环带最宽、正南中高仰角带最密，说明本场太阳多处于中低高度角，建筑自遮挡与周边遮挡会被放大。',
        '中：每个天穹位置的平均干球温度——南偏西的低仰角傍晚位置最热，正午高仰角位置反而偏凉，指示"西晒"是主要得热矛盾。',
        '右：每个位置的平均太阳总辐射——高值沿偏南中高仰角带分布，与中图的温度高值区并不重合，是遮阳与被动得热按时段分开设计的依据。',
    ], fs=7.0, color='#444444')
    P.header(fig, '太阳轨迹天穹图  ·  位置 → 气候值',
             'Sun-Path Dome · 全年 8,760 h 太阳位置聚类 5° 蜂窝格 · 等距投影（半径 = 90° − 高度角）')
    P.footer(fig, P.dateline())
    return P.save(fig, '02_太阳轨迹', '03_太阳轨迹天穹图_位置与气候值.png')


# ------------------------------------------------------------------ 类型 5
def fig_3d_surface():
    bins = np.arange(-4, 40.5, 1.5)
    hbins = np.arange(0, 25, 1)
    seasons = [('全年', np.ones_like(MONH, dtype=bool), '#3A6EA5'),
               ('夏季 6–8 月', np.isin(MONH, [6, 7, 8]), '#C0392B'),
               ('冬季 12–2 月', np.isin(MONH, [12, 1, 2]), '#2E75B6'),
               ('过渡季 3–5 / 9–11 月', np.isin(MONH, [3, 4, 5, 9, 10, 11]), '#548235')]

    fig = plt.figure(figsize=(16.0, 10.4))
    for i, (nm, sel, col) in enumerate(seasons):
        r, c = divmod(i, 2)
        ax = fig.add_axes([0.045 + c * 0.50, 0.515 - r * 0.455, 0.415, 0.375],
                          projection='3d')
        Hh, xe, ye = np.histogram2d(TA[sel], HOURLY_H[sel],
                                    bins=[bins, hbins])
        Hh = Hh.T
        xs = (xe[:-1] + xe[1:]) / 2
        ys = (ye[:-1] + ye[1:]) / 2
        Xg, Yg = np.meshgrid(xs, ys)
        dx = (xe[1] - xe[0]) * 0.9
        dy = (ye[1] - ye[0]) * 0.9
        mask = Hh > 0
        norm = plt.Normalize(0, Hh.max() * 0.85)
        cmap = plt.get_cmap('YlOrRd')
        colors = cmap(norm(Hh))
        ax.bar3d(Xg[mask].ravel(), Yg[mask].ravel(), np.zeros(mask.sum()),
                 dx, dy, Hh[mask].ravel(),
                 color=colors[mask].reshape(-1, 4), shade=True, zsort='max')
        ax.set_xlabel('干球温度 (°C)', fontsize=7.6, labelpad=-2)
        ax.set_ylabel('钟点 (h)', fontsize=7.6, labelpad=-2)
        ax.set_zlabel('小时数', fontsize=7.6, labelpad=-2)
        ax.set_xlim(-4, 40)
        ax.set_ylim(0, 24)
        ax.set_zlim(0, Hh.max() * 1.05)
        ax.tick_params(labelsize=6.2)
        ax.view_init(elev=24, azim=-58)
        ax.set_box_aspect((1.5, 1.0, 0.62))
        ax.set_title(nm, fontsize=10.5, color=col, pad=-2)
        ax.grid(True, lw=0.4, alpha=0.4)

    P.header(fig, '干球温度 × 钟点 三维频次曲面',
             '3D Temperature-Hour Frequency Surface · 柱高 = 该「温度—钟点」组合全年出现的小时数', y=0.978)
    P.caption(fig, 0.045, 0.055, [
        '读图：柱高 = 该「温度—钟点」组合全年出现的小时数。全年最密的一格是 22.2 °C / 19 时（35 h），温度主脊落在 22.2 °C——本场出现最多的温度并不冷，冬季时长由大范围低温平摊而成，不是尖峰。',
        '夏季（6–8 月）：温度主脊右移到 26.8 °C，且该季最热的 10 % 小时集中在 14 时前后——指向午后西向遮阳与蓄冷需求。',
        '冬季（12–2 月）：温度主脊降到 4.2 °C，该季最热的 10 % 小时集中在 15 时、最冷段落在清晨——指向夜间保温与晨间预热策略。',
        '过渡季（3–5 / 9–11 月）：温度主脊 20.8 °C，正落在自然通风最有效的区间（本场自然通风可用小时占 37.9 % = 3,323 h）。',
    ], fs=7.2, color='#444444')
    P.footer(fig, P.dateline('温度分箱 1.5 K'))
    return P.save(fig, '05_三维曲面', '01_温度钟点频次曲面.png')


def fig_3d_surface_tri():
    """三参数两两组合的出现频次曲面（全年）

    对应参考图中下半部右列的三张曲面：把「干球温度」分别与
    相对湿度 / 太阳总辐射 / 风速 做二维分箱，柱高 = 该组合全年出现小时数。
    """
    jobs = [
        ('干球温度 × 相对湿度', TA, RH, np.arange(-4, 40.5, 1.5),
         np.arange(20, 101, 5), '干球温度 (°C)', '相对湿度 (%)', '#2E75B6'),
        ('干球温度 × 太阳总辐射', TA, GHI, np.arange(-4, 40.5, 1.5),
         np.arange(0, 1001, 50), '干球温度 (°C)', '总辐射 GHI (W/m²)', '#BE2F27'),
        ('干球温度 × 风速', TA, WS, np.arange(-4, 40.5, 1.5),
         np.arange(-0.25, 9.5, 0.5), '干球温度 (°C)', '风速 (m/s)', '#548235'),
    ]

    fig = plt.figure(figsize=(17.4, 7.6))
    for i, (title, xv, yv, xb, yb, xl, yl, col) in enumerate(jobs):
        ax = fig.add_axes([0.012 + i * 0.330, 0.185, 0.290, 0.615],
                          projection='3d')
        Hh, xe, ye = np.histogram2d(xv, yv, bins=[xb, yb])
        Hh = Hh.T
        xs = (xe[:-1] + xe[1:]) / 2
        ys = (ye[:-1] + ye[1:]) / 2
        Xg, Yg = np.meshgrid(xs, ys)
        mask = Hh > 0
        norm = plt.Normalize(0, Hh.max())
        cmap = plt.get_cmap('YlOrRd')
        colors = cmap(norm(Hh))
        ax.bar3d(Xg[mask].ravel(), Yg[mask].ravel(), np.zeros(int(mask.sum())),
                 (xe[1] - xe[0]) * 0.9, (ye[1] - ye[0]) * 0.9, Hh[mask].ravel(),
                 color=colors[mask].reshape(-1, 4), shade=True, zsort='max')
        ax.set_xlabel(xl, fontsize=7.6, labelpad=-1)
        ax.set_ylabel(yl, fontsize=7.6, labelpad=-2)
        ax.set_zlabel('小时数', fontsize=7.4, labelpad=-2)
        ax.set_xlim(xb[0], xb[-1])
        ax.set_ylim(yb[0], yb[-1])
        ax.set_zlim(0, Hh.max() * 1.05)
        ax.tick_params(labelsize=6.0)
        ax.view_init(elev=26, azim=-62)
        ax.set_box_aspect((1.45, 1.0, 0.60))
        ax.grid(True, lw=0.4, alpha=0.4)
        peak = np.unravel_index(int(np.argmax(Hh)), Hh.shape)
        ax.set_title('%s\n峰值 %d h  @ %.0f°C / %.0f' %
                     (title, int(Hh.max()), xs[peak[1]], ys[peak[0]]),
                     fontsize=9.4, color=col, pad=-4)

    P.caption(fig, 0.012, 0.040, [
        '读图：三张曲面把"干球温度"分别与相对湿度、太阳总辐射、风速做二维分箱，柱高 = 该组合全年出现的小时数；三图共用同一温度分箱（1.5 K），便于横向对照。',
        '温度 × 湿度：主峰落在 22 °C / 90–95 %（128 h）；16–22 °C 且 RH ≥ 85 % 的"温和但潮湿"小时全年有 740 h（占 8.4 %）——这是过渡季舒适度上不去的主因。',
        '温度 × 辐射：最高频组合是 22 °C / 25 W/m²（415 h）。在 24–30 °C 的偏热小时里，GHI < 100 W/m² 的有 951 h，反而多于 GHI ≥ 300 W/m² 的 552 h——偏热时段近六成不是晒热而是高湿闷热，遮阳不能只按辐射峰值定。',
        '温度 × 风速：峰值 175 h @ 22 °C / 3 m/s。高温时段风速并未衰减（TA ≥ 30 °C 平均 3.69 m/s，高于全年 3.25 m/s；TA ≥ 28 °C 时风速 ≤ 2 m/s 的小时占比 26 %，低于 TA < 24 °C 时的 34 %）——本场夏季仍有可用的穿堂风资源，保留南北贯通风道有实际收益。',
    ], fs=6.9, color='#444444')
    P.header(fig, '三参数两两组合 · 三维频次曲面',
             '3D Frequency Surfaces · 干球温度 × 相对湿度 / 太阳总辐射 / 风速 · 全年 8,760 h', y=0.972)
    P.footer(fig, P.dateline())
    return P.save(fig, '05_三维曲面', '02_三参数组合频次曲面.png')


if __name__ == '__main__':
    fig_sunpath((90.0, 20.0, 1.5), False, '01_太阳轨迹_全年.png',
                title_extra='观测点：场地南侧空地 (90, 20)')
    fig_sunpath_shading()
    fig_sunpath_dome()
    fig_3d_surface()
    fig_3d_surface_tri()
    print('--- 类型 2 / 5 完成 ---')
