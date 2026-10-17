# -*- coding: utf-8 -*-
"""图集总图版

复刻 Ladybug Climate Analysis 的版式语言：
上半 = 极坐标图矩阵（逐月风玫瑰）
下半 = 四列并置（太阳轨迹 / 逐时热图 / 月度图表 / 场地日照）
"""
import json
import math
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Polygon as MplPolygon

import plot_common as P
import climate_engine as E
from plot_common import horizon_profile as _horizon_profile, MONTH_COLORS

CD = P.load_climate()
OBJS = E.load_building()
TRIS, _ = E.all_triangles(OBJS)
HF, CELL = E.build_heightfield(TRIS, cell=1.0, zmax=40.0)

with open(os.path.join(P.DATA, 'epw_hourly.json'), encoding='utf-8') as f:
    R = json.load(f)
R_MON = np.array(R['month'], dtype=int)
R_DAY = np.array(R['day'], dtype=int)
R_HR = np.array(R['hour'], dtype=int)
R_TA = np.array(R['ta'], dtype=float)
R_GHI = np.array(R['ghi'], dtype=float)
R_WS = np.array(R['wind_spd'], dtype=float)
R_WD = np.array(R['wind_dir'], dtype=float)

CUM = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
DOY = CUM[R_MON - 1] + R_DAY
CUMH = np.array(CD['hourly']['month'], dtype=int)
ALTH = np.array(CD['sunpath']['altitude_hourly'], dtype=float)
AZIH = np.array(CD['sunpath']['azimuth_hourly'], dtype=float)
ARCS = CD['sunpath']['arcs']
NORTH = E.true_north_in_model()
SUN = P.load_extra('sunhours_grid.json')
SHADOW_CMAP = ListedColormap(['#62707E', '#FBF2D6'])

CALM = R_WS < 0.5
SPEED_BINS = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 1e9]


def wind_matrix(sel):
    wd = R_WD[sel][~CALM[sel]]
    ws = R_WS[sel][~CALM[sel]]
    idx = np.floor((wd + 11.25) % 360.0 / 22.5).astype(int) % 16
    m = np.zeros((16, 7), dtype=int)
    for k in range(7):
        s = (ws >= SPEED_BINS[k]) & (ws < SPEED_BINS[k + 1])
        np.add.at(m[:, k], idx[s], 1)
    return m


def draw_building(ax, fc='#8C8C8C', ec='#4A4A4A', lw=0.3, z=5):
    for t in TRIS:
        ax.add_patch(MplPolygon(t[:, :2], closed=True, facecolor=fc,
                                edgecolor=ec, linewidth=lw, zorder=z))


def draw_north(ax, x, y, L, fs, col='#333333'):
    ax.annotate('', xy=(x + NORTH[0] * L, y + NORTH[1] * L), xytext=(x, y),
                arrowprops=dict(arrowstyle='-|>', color=col, lw=1.4), zorder=9)
    ax.text(x + NORTH[0] * L * 1.30, y + NORTH[1] * L * 1.30, 'N',
            fontsize=fs, color=col, ha='center', va='center', weight='bold', zorder=9)


def main():
    FW, FH = 30.0, 21.0
    fig = plt.figure(figsize=(FW, FH))
    ratio = FW / FH          # 正方形轴需要的 h/w 比

    # ---------------------------------------------------------- 页眉
    fig.text(0.022, 0.982, P.L('title', '气候前期分析图集'),
             fontsize=27, weight='bold', color='#1A1A1A', va='top')
    fig.text(0.022, 0.955,
             'Climate Analysis Atlas  ·  %s  ·  %s  ·  %d h'
             % (P.L('site_address', P.site_name_line()), P.station_label(),
                    CD['meta']['records']),
             fontsize=12.5, color='#666666', va='top')
    fig.add_artist(plt.Line2D([0.022, 0.978], [0.938, 0.938],
                              transform=fig.transFigure, color='#C8C8C8', lw=1.0))

    # ========================================================== 上半：逐月风玫瑰
    fig.text(0.022, 0.925, 'A  逐月风玫瑰矩阵', fontsize=13.5, weight='bold',
             color='#222222', va='top')
    fig.text(0.235, 0.9265, 'Monthly Wind Rose Matrix  ·  16 方位 × 7 风速级  ·  各月统一径向刻度',
             fontsize=9.6, color='#777777', va='top')

    rmax_all = 0
    mats, phs = [], []
    for mo in range(1, 13):
        sel = (R_MON == mo)
        m = wind_matrix(sel)
        mats.append(m)
        phs.append(int(sel.sum()))
        rmax_all = max(rmax_all, m.sum(axis=1).max() / max(int(sel.sum()), 1) * 100)
    rmax_all = math.ceil(rmax_all / 5.0) * 5

    for i in range(12):
        r, c = divmod(i, 6)
        ax = fig.add_axes([0.024 + c * 0.1350, 0.758 - r * 0.156, 0.105,
                           0.105 * ratio], projection='polar')
        P.draw_windrose(ax, mats[i], phs[i], rmax=rmax_all, ring_step=5,
                        width_frac=0.82)
        ax.tick_params(labelsize=5.2)
        ax.set_title('%d 月' % (i + 1), fontsize=8.6, pad=-8, color='#222222')
        per = mats[i].sum(axis=1) / float(phs[i]) * 100
        from plot_common import ensure as _e
        ax.text(0, 0, '%0.0f%%' % ((R_WS[R_MON == i + 1] < 0.5).mean() * 100),
                ha='center', va='center', fontsize=5.0, color='#666666', zorder=6)

    # 右侧说明
    P.speed_legend(fig, 0.852, 0.855, fs=8.2, box_h=0.014, box_w=0.010, gap=0.002)
    P.caption(fig, 0.852, 0.735, [
        '读图',
        '扇长 = 该方向出现频率',
        '（占该月全部小时）',
        '颜色 = 风速分级',
        '中心数字 = 静风率',
        '',
        '季节规律',
        '冬（12–2 月）偏北风为主',
        '夏（6–8 月）东南风增强',
        '春（3–5 月）风向最分散',
        '',
        '全年主导风向 NE 东北',
        '年平均风速 3.25 m/s',
    ], fs=8.4, color='#444444', lh=1.45)

    # ========================================================== 下半：四列
    Y0, CH = 0.285, 0.255           # 下半列底 / 正方形高
    CW = CH / ratio
    XS = [0.024, 0.256, 0.488, 0.734]

    # ---- 列 1：太阳轨迹（内院视角 + 建筑遮挡）
    fig.text(XS[0], 0.572, 'B  太阳轨迹与建筑遮挡', fontsize=13.0, weight='bold',
             color='#222222', va='top')
    fig.text(XS[1], 0.5735, 'Sun Path  ·  观测点：西内院中心 (50, 82)  ·  等距投影  半径 = 90° − 高度角',
             fontsize=9.4, color='#777777', va='top')
    ax = fig.add_axes([XS[0], Y0, CW, CH], projection='polar')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    vp = P.viewpoint('sunpath')
    azp, prof = _horizon_profile(HF, CELL, vp[0], vp[1], vp[2])
    thp = np.radians(azp)
    rp = 90 - prof
    ax.plot(np.append(thp, thp[0]), np.append(rp, rp[0]), color='#4A4A4A', lw=1.7,
            zorder=6)
    ax.fill(np.append(thp, thp[0]), np.append(rp, rp[0]), color='#DCDCDC',
            alpha=0.75, zorder=5)
    for arc in ARCS:
        pts = [p for p in arc['points'] if p[1] > 0]
        if len(pts) < 2:
            continue
        ax.plot(np.radians([p[2] for p in pts]), 90 - np.array([p[1] for p in pts]),
                '-', color=MONTH_COLORS[arc['month'] - 1],
                lw=2.2 if arc['month'] in (6, 12) else 1.0, zorder=7)
    for a in (0, 15, 30, 45, 60, 75):
        tt = np.linspace(0, 2 * math.pi, 120)
        ax.plot(tt, np.full_like(tt, 90 - a), color='#E4E4E4', lw=0.6, zorder=1)
    ax.set_ylim(90, 0)
    ax.set_yticks([90 - a for a in (0, 30, 60, 75)])
    ax.set_yticklabels(['0°', '30°', '60°', '75°'], fontsize=6.2, color='#AAAAAA')
    ax.set_xticks(np.arange(16) / 16 * 2 * math.pi)
    ax.set_xticklabels(['N', '', 'NE', '', 'E', '', 'SE', '', 'S', '', 'SW', '',
                        'W', '', 'NW', ''], fontsize=6.6)
    ax.grid(color='#F0F0F0', lw=0.5)
    ax.set_title('灰区 = 建筑遮挡天空\n轮廓线上方（外圈）为可见天空',
                 fontsize=7.4, color='#555555', pad=8)

    # ---- 列 2：逐时温度热图
    fig.text(XS[1] + 0.002, 0.572, 'C  逐时气象热图', fontsize=13.0, weight='bold',
             color='#222222', va='top')
    params = [('干球温度 °C', R_TA, 0, 36, 'RdYlBu_r'),
              ('相对湿度 %', np.array(R['rh'], float), 20, 100, 'YlGnBu'),
              ('太阳总辐射 Wh/m²', R_GHI, 0, 950, 'YlOrRd')]
    hh = 0.062
    for j, (nm, vals, v0, v1, cmap) in enumerate(params):
        ax = fig.add_axes([XS[1] + 0.002, Y0 + 0.190 - j * 0.084, CW * 0.86, hh])
        g = np.full((365, 24), np.nan)
        g[DOY - 1, R_HR] = vals
        im = ax.imshow(g, aspect='auto', origin='lower', extent=[0, 24, 1, 366],
                       cmap=cmap, vmin=v0, vmax=v1, interpolation='nearest')
        ax.set_xticks([0, 6, 12, 18, 24])
        ax.set_xticklabels(['0', '6', '12', '18', '24'], fontsize=5.8)
        ax.set_yticks(CUM + 15)
        ax.set_yticklabels(['%d' % m for m in range(1, 13)], fontsize=5.6)
        ax.set_title(nm, fontsize=7.6, loc='left', pad=2, color='#333333')
        cax = fig.add_axes([XS[1] + 0.002 + CW * 0.87, Y0 + 0.190 - j * 0.084 + 0.008,
                            0.006, hh - 0.016])
        cb = fig.colorbar(im, cax=cax)
        cb.ax.tick_params(labelsize=5.0)
        ax.grid(False)
        for s in ax.spines.values():
            s.set_color('#CCCCCC')

    # ---- 列 3：月度图表
    fig.text(XS[2], 0.572, 'D  月度气候图表', fontsize=13.0, weight='bold',
             color='#222222', va='top')
    mo = CD['monthly']
    M = np.arange(1, 13)
    ta_m = np.array(mo['ta_mean'], float)
    ta_hi = np.array(mo['ta_max'], float)
    ta_lo = np.array(mo['ta_min'], float)
    rh_m = np.array(mo['rh_mean'], float)
    ghi_m = np.array(mo['ghi_total'], float) / 1000
    ws_m = np.array(mo['ws_mean'], float)

    ax1 = fig.add_axes([XS[2] + 0.002, Y0 + 0.165, CW * 0.90, 0.086])
    ax1.fill_between(M, ta_lo, ta_hi, color='#F2C4B0', alpha=0.85, label='月极值')
    ax1.plot(M, ta_m, '-o', color='#C1553B', lw=1.5, ms=3.0, label='月均温度')
    ax1.set_ylabel('°C', fontsize=6.6)
    ax1.set_xticks(M)
    ax1.set_xticklabels(['%d' % m for m in M], fontsize=5.8)
    ax1.set_ylim(-8, 40)
    ax1.legend(fontsize=5.6, loc='upper left', ncol=2)
    ax1.set_title('干球温度', fontsize=7.6, loc='left', pad=2, color='#333333')
    ax1.tick_params(labelsize=5.6)

    ax2 = fig.add_axes([XS[2] + 0.002, Y0 + 0.052, CW * 0.90, 0.086])
    ax2.bar(M, ghi_m, color='#EFA135', width=0.62, label='水平面辐射')
    ax2.set_ylabel('kWh/m²', fontsize=6.6)
    ax2.set_xticks(M)
    ax2.set_xticklabels(['%d' % m for m in M], fontsize=5.8)
    ax2.legend(fontsize=5.6, loc='upper left')
    ax2.set_title('太阳辐射月总量', fontsize=7.6, loc='left', pad=2, color='#333333')
    ax2.tick_params(labelsize=5.6)

    # 右列小字
    P.caption(fig, XS[2] + 0.002, Y0 - 0.012, [
        '全年均值：温度 %0.1f °C ｜ 相对湿度 %0.0f%% ｜ 风速 %0.2f m/s'
        % (np.mean(R_TA), np.mean(np.array(R['rh'], float)), np.mean(R_WS)),
        'HDD18 = %0.0f  ·  CDD26 = %0.0f  →  冬季权重约为夏季 10 倍，以防寒保温为优先'
        % (CD['indicators']['hdd18'], CD['indicators']['cdd26']),
        '自然通风可用 %0.1f%%  ·  舒适区间仅 %0.1f%%  ·  露点 > 20 °C 占 %0.1f%%'
        % (CD['indicators']['natural_vent_pct'], CD['indicators']['comfort_pct'],
           CD['indicators']['dehumid_pct']),
    ], fs=7.4, color='#555555', lh=1.5)

    # ---- 列 4：场地日照率
    fig.text(XS[3], 0.572, 'E  场地日照率（含建筑遮挡）', fontsize=13.0, weight='bold',
             color='#222222', va='top')
    xs = np.array(SUN['xs'], float)
    ys = np.array(SUN['ys'], float)
    co = np.array(SUN['coords'], float)
    step = SUN['step']
    ii = np.rint((co[:, 0] - xs[0]) / step).astype(int)
    jj = np.rint((co[:, 1] - ys[0]) / step).astype(int)
    g = np.full((len(ys), len(xs)), np.nan)
    g[jj, ii] = np.array(SUN['hours_year'], float) / SUN['season_hours']['year'] * 100
    X, Y = np.meshgrid(xs, ys)

    axA = fig.add_axes([XS[3] + 0.004, Y0 + 0.004, CW * 0.96, CW * 0.96 * ratio])
    m = axA.pcolormesh(X, Y, g, cmap='YlOrRd', vmin=0, vmax=100,
                       shading='nearest', zorder=2)
    draw_building(axA, fc='#7A7A7A', ec='#3D3D3D', lw=0.2, z=5)
    axA.set_aspect('equal')
    P.site_axis(axA, 3, 5.6)
    axA.grid(color='#EFEFEF', lw=0.5)
    draw_north(axA, P.SX1 - 0.12 * (P.SX1 - P.SX0), P.SY0 + 0.045 * (P.SY1 - P.SY0), L=20, fs=7.0)
    ca = fig.add_axes([XS[3] + 0.004 + CW * 0.965, Y0 + 0.030, 0.007, 0.20])
    cb = fig.colorbar(m, cax=ca)
    cb.set_label('日照率 %', fontsize=6.0)
    cb.ax.tick_params(labelsize=5.4)

    # 阴影小图（夏至正午）
    axB = fig.add_axes([XS[3] + 0.008, Y0 + 0.008, CW * 0.90, CW * 0.90 * ratio * 0.42])
    k = int(np.where((CUMH == 6) & (np.array(CD['hourly']['day'], int) == 21)
                     & (np.array(CD['hourly']['hour'], int) == 12))[0][0])
    xs2, ys2 = P.site_grid(3.0)
    GX, GY = np.meshgrid(xs2, ys2)
    PX = GX.ravel().astype(np.float32)
    PY = GY.ravel().astype(np.float32)
    PZ = np.full(PX.size, 0.05, dtype=np.float32)
    d = E.sun_dirs(ALTH[k:k + 1], AZIH[k:k + 1])
    lit = E.sunlit(PX, PY, PZ, d, HF, cell=CELL, step=2.0, zmax=30.0)
    gm = lit[:, 0].reshape(GX.shape).astype(float)
    axB.pcolormesh(GX, GY, gm, cmap=SHADOW_CMAP, vmin=0, vmax=1,
                   shading='nearest', zorder=1)
    draw_building(axB, fc='#4D4D4D', ec='#2A2A2A', lw=0.2, z=5)
    axB.set_aspect('equal')
    P.site_axis(axB, 3, 5.6)
    axB.grid(color='#EFEFEF', lw=0.5)
    axB.set_title('夏至 6/21 12:00 阴影（高度角 82°）', fontsize=6.8, pad=2,
                  color='#444444')

    P.caption(fig, XS[3] + 0.004, Y0 - 0.012, [
        '内院是全年日照低谷，中心仅约 28%（约 1 200 h）。',
        '场地四周空地日照率 > 85%，南侧空场冬季仍可获连续日照。',
    ], fs=7.2, color='#555555', lh=1.4)

    # ---------------------------------------------------------- 页脚
    fig.add_artist(plt.Line2D([0.022, 0.978], [0.048, 0.048],
                              transform=fig.transFigure, color='#C8C8C8', lw=1.0))
    fig.text(0.022, 0.032,
             P.source_line(extra='三角面 %d' % len(TRIS)),
             fontsize=8.0, color='#888888', va='top')
    fig.text(0.978, 0.032, P.L('footer_right', ''), fontsize=8.0,
             color='#888888', va='top', ha='right')

    p = os.path.join(P.OUTROOT, '00_气候分析总图版.png')
    fig.savefig(p, dpi=150, facecolor='white')
    plt.close(fig)
    print('saved:', p)


if __name__ == '__main__':
    main()
