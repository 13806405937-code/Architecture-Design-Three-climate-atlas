# -*- coding: utf-8 -*-
"""类型 1 · 极坐标玫瑰族
风玫瑰（全年 / 逐月 / 四季）、主导风向罗盘、太阳辐射玫瑰、日照时数玫瑰
"""
import math
import os

import numpy as np
import matplotlib.pyplot as plt

import plot_common as P

DIR16 = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
         'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
SPEED_BINS = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 1e9]

CD = P.load_climate()
H = CD['hourly']
WD = np.array(H['wd'], dtype=float)      # 风来向（自北顺时针）
WS = np.array(H['ws'], dtype=float)
MON = np.array(H['month'], dtype=int)
GHI = np.array(H['ghi'], dtype=float)
DNI = np.array(H['dni'], dtype=float)
DHI = np.array(H['dhi'], dtype=float)
ALT = np.array(CD['sunpath']['altitude_hourly'], dtype=float)
AZI = np.array(CD['sunpath']['azimuth_hourly'], dtype=float)

CALM = WS < 0.5                          # 静风判据


# ------------------------------------------------------------------ 工具
def wind_matrix(sel=None, ws=None, wd=None):
    """返回 (16,7) 小时数矩阵。sel 为布尔掩膜。"""
    wd = WD if wd is None else wd
    ws = WS if ws is None else ws
    if sel is not None:
        wd = wd[sel]
        ws = ws[sel]
    calm = ws < 0.5
    wd = wd[~calm]
    ws = ws[~calm]
    idx = (np.floor((wd + 11.25) % 360.0 / 22.5)).astype(int) % 16
    m = np.zeros((16, 7), dtype=int)
    for k in range(7):
        s = (ws >= SPEED_BINS[k]) & (ws < SPEED_BINS[k + 1])
        np.add.at(m[:, k], idx[s], 1)
    return m


def rose_stats(m, calm_mask=None, period_hours=None):
    cm = CALM if calm_mask is None else calm_mask
    total = m.sum()
    ph = total + int(cm.sum()) if period_hours is None else int(period_hours)
    per_dir = m.sum(axis=1)
    top = int(np.argmax(per_dir))
    return dict(total=total, period_hours=ph, per_dir=per_dir,
                dominant=DIR16[top], dominant_pct=per_dir[top] / max(ph, 1) * 100,
                calm_pct=cm.mean() * 100, calm_h=int(cm.sum()))


def rose_caption(st, period):
    lines = [
        '风速 (m/s) · %s' % P.station_label(),
        '时段：%s' % period,
        '静风 %0.2f%% = %d 小时' % (st['calm_pct'], st['calm_h']),
        '最多风向 %s  占 %0.2f%%' % (st['dominant'], st['dominant_pct']),
    ]
    return lines


# ------------------------------------------------------------------ 1. 全年风玫瑰
def fig_annual():
    fig = plt.figure(figsize=(9.6, 8.2))
    ax = fig.add_axes([0.075, 0.17, 0.60, 0.66], projection='polar')

    m = wind_matrix()
    st = rose_stats(m, CALM, 8760)
    rmax, bot = P.draw_windrose(ax, m, st['period_hours'], rmax=None, ring_step=2)
    P.caption(fig, 0.075, 0.125, rose_caption(st, '全年 1/1 – 12/31，0–23 时'))

    # 静风中心圈
    ax.text(0, 0, '%0.1f%%\n静风' % st['calm_pct'], ha='center', va='center',
            fontsize=8.5, color='#555555', zorder=6)

    # 主导风向指示
    ang = DIR16.index(st['dominant']) * (2 * math.pi / 16)
    ax.annotate('', xy=(ang, rmax * 1.04), xytext=(ang, rmax * 0.60),
                arrowprops=dict(arrowstyle='-|>', color='#BE2F27', lw=1.6), zorder=7)

    P.speed_legend(fig, 0.715, 0.66)
    P.caption(fig, 0.715, 0.475, [
        '径向 = 该方向出现频率 (%)',
        '环形刻度每 2% 一格',
        '颜色 = 风速分级',
        '扇形总和 = 100% − 静风率', '',
        '年平均风速 %0.2f m/s' % WS.mean(),
        '最大风速 %0.1f m/s' % WS.max(), '',
        '主导风向 %s  占 %0.2f%%' % (st['dominant'], st['dominant_pct']), '',
    ] + P.regime_note(CD), color='#444444')
    P.header(fig, '全年风玫瑰', 'Wind Rose · %s · 16 方位 × 7 风速级' % P.station_label())
    P.footer(fig, P.dateline('风向为「风来向」  |  静风阈值 <0.5 m/s'))
    return P.save(fig, '01_极坐标玫瑰', '01_风玫瑰_全年.png')


# ------------------------------------------------------------------ 2. 逐月矩阵
def fig_monthly():
    fig = plt.figure(figsize=(15.6, 11.0))
    months = list(range(1, 13))
    mats, stats, phs = [], [], []
    for mo in months:
        sel = (MON == mo)
        m = wind_matrix(sel)
        mats.append(m)
        phs.append(int(sel.sum()))
        stats.append(rose_stats(m, CALM & sel, int(sel.sum())))
    rmax_all = max(np.max(m.sum(axis=1)) / ph * 100 for m, ph in zip(mats, phs))
    rmax_all = math.ceil(rmax_all / 5.0) * 5

    for i, mo in enumerate(months):
        r, c = divmod(i, 4)
        x0 = 0.028 + c * 0.2455
        y0 = 0.655 - r * 0.262
        ax = fig.add_axes([x0, y0, 0.205, 0.205], projection='polar')
        m = mats[i]
        st = stats[i]
        P.draw_windrose(ax, m, phs[i], rmax=rmax_all, ring_step=5, width_frac=0.82)
        ax.set_title('%d 月' % mo, fontsize=12, pad=-16, color='#222222')
        ax.text(0, 0, '%0.0f%% 静风' % st['calm_pct'], ha='center', va='center',
                fontsize=5.8, color='#666666', zorder=6)
        P.caption(fig, x0, y0 - 0.020,
                  ['主导 %s  %0.1f%%' % (st['dominant'], st['dominant_pct']),
                   '样本 %d h · 静风 %d h' % (phs[i], st['calm_h'])], fs=6.3)

    P.speed_legend_h(fig, 0.045, x0=0.30)
    P.header(fig, '逐月风玫瑰矩阵',
             'Monthly Wind Rose Matrix · 12 个月 × 16 方位 × 7 风速级  |  各月使用相同径向刻度 0–%d%% 便于横向比较' % rmax_all)
    P.footer(fig, P.dateline('扇长为该方向出现频率（占该月全部小时）'))
    return P.save(fig, '01_极坐标玫瑰', '02_风玫瑰_逐月矩阵.png')


# ------------------------------------------------------------------ 3. 四季
def fig_seasons():
    fig = plt.figure(figsize=(11.4, 11.5))
    seasons = [('春 3–5 月', np.isin(MON, [3, 4, 5]), '#548235'),
               ('夏 6–8 月', np.isin(MON, [6, 7, 8]), '#C00000'),
               ('秋 9–11 月', np.isin(MON, [9, 10, 11]), '#BF8F00'),
               ('冬 12–2 月', np.isin(MON, [12, 1, 2]), '#2E75B6')]
    mats = [wind_matrix(sel) for _, sel, _ in seasons]
    phs = [int(sel.sum()) for _, sel, _ in seasons]
    rmax = math.ceil(max(m.sum(axis=1).max() / ph * 100
                         for m, ph in zip(mats, phs)) / 5) * 5

    for i, ((name, sel, col), m) in enumerate(zip(seasons, mats)):
        r, c = divmod(i, 2)
        ax = fig.add_axes([0.07 + c * 0.47, 0.520 - r * 0.450, 0.36, 0.36],
                          projection='polar')
        P.draw_windrose(ax, m, phs[i], rmax=rmax, ring_step=5)
        st = rose_stats(m, CALM & sel, phs[i])
        ax.set_title(name, fontsize=13, pad=-22, color=col, weight='bold')
        ax.text(0, 0, '%0.1f%%\n静风' % st['calm_pct'], ha='center', va='center',
                fontsize=7.4, color='#555555', zorder=6)
        P.caption(fig, 0.07 + c * 0.47, 0.520 - r * 0.450 - 0.010,
                  ['主导风向 %s  占 %0.1f%%' % (st['dominant'], st['dominant_pct']),
                   '样本 %d h · 静风 %d h' % (st['total'], st['calm_h']),
                   '平均风速 %0.2f m/s' % WS[sel].mean()], fs=7.0)

    P.speed_legend(fig, 0.80, 0.90, fs=7.2)
    P.caption(fig, 0.80, 0.83, [
        '径向 = 频率 (%) · 刻度 5%',
        '',
    ] + P.regime_note(CD) + P.design_notes(), fs=7.2, color='#444444')
    P.header(fig, '四季风玫瑰对比', 'Seasonal Wind Rose · 相同的径向刻度便于横向比较')
    P.footer(fig, P.dateline())
    return P.save(fig, '01_极坐标玫瑰', '03_风玫瑰_四季对比.png')


# ------------------------------------------------------------------ 4. 主导风向罗盘
def fig_prevailing():
    fig = plt.figure(figsize=(9.2, 8.6))
    ax = fig.add_axes([0.10, 0.14, 0.66, 0.70], projection='polar')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)

    periods = [('全年', np.ones_like(MON, dtype=bool), '#333333'),
               ('春', np.isin(MON, [3, 4, 5]), '#548235'),
               ('夏', np.isin(MON, [6, 7, 8]), '#C00000'),
               ('秋', np.isin(MON, [9, 10, 11]), '#BF8F00'),
               ('冬', np.isin(MON, [12, 1, 2]), '#2E75B6')]

    allm = wind_matrix()
    rmax = allm.sum(axis=1).max() / allm.sum() * 100 * 1.25
    for i, (name, sel, col) in enumerate(periods):
        m = wind_matrix(sel)
        per = m.sum(axis=1) / m.sum() * 100
        ang = np.arange(16) * (2 * math.pi / 16)
        rr = rmax * 0.42 + i * 0.0
        # 用细箭头的方向指示（每个时期一组长短不同的箭头）
        ax.quiver(ang, np.full(16, rr), np.zeros(16), per,
                  color=col, width=0.006, headwidth=3.2, headlength=4.2,
                  alpha=0.85, zorder=4)
        top = int(np.argmax(per))
        ax.annotate(name, xy=(ang[top], rr + per[top] + rmax * 0.05),
                    fontsize=10, color=col, ha='center', va='center',
                    weight='bold', zorder=6)

    ticks = np.arange(2, rmax * 0.42 + 1, 2)
    ax.set_ylim(0, rmax * 0.42 + rmax * 0.30)
    ax.set_yticks(np.arange(0, rmax, 5))
    ax.set_yticklabels(['%d%%' % v for v in np.arange(0, rmax, 5)],
                       fontsize=7, color='#999999')
    th = np.arange(16) / 16 * 2 * math.pi
    ax.set_xticks(th)
    ax.set_xticklabels(DIR16, fontsize=8)
    ax.grid(color='#E0E0E0', lw=0.6)
    ax.text(0, 0, '', ha='center')

    P.header(fig, '主导风向与频率分布', 'Prevailing Winds · 箭头长度 = 该方向出现频率')
    P.caption(fig, 0.10, 0.105, [
        '各方向扇区频率 (%)，5 个时期并列比较。',
    ] + P.regime_note(CD), fs=8.0)
    P.caption(fig, 0.80, 0.86, ['颜色对照', '', '黑 全年', '绿 春', '红 夏',
                                '黄 秋', '蓝 冬'], fs=8.0, color='#444444')
    P.footer(fig, P.dateline())
    return P.save(fig, '01_极坐标玫瑰', '04_主导风向罗盘.png')


# ------------------------------------------------------------------ 5. 太阳辐射玫瑰
def fig_rad_rose():
    """各朝向垂直面全年接收的太阳辐射（无遮挡，气象上限）"""
    E = np.sin(np.radians(AZI)) * np.cos(np.radians(ALT))
    N = np.cos(np.radians(AZI)) * np.cos(np.radians(ALT))
    U = np.sin(np.radians(ALT))
    up = U > 0

    tilt = 90.0
    kd = (1 + math.cos(math.radians(tilt))) / 2.0
    kr = 0.2 * (1 - math.cos(math.radians(tilt))) / 2.0
    vals = np.zeros(16)
    for k in range(16):
        af = math.radians(k * 22.5)
        cos_i = np.clip(E * math.sin(af) + N * math.cos(af), 0, None) * up
        beam = DNI * cos_i
        vals[k] = (beam + DHI * kd + GHI * kr).sum() / 1000.0

    fig = plt.figure(figsize=(9.6, 8.4))
    ax = fig.add_axes([0.085, 0.16, 0.60, 0.68], projection='polar')
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    th = np.arange(16) * (2 * math.pi / 16)
    cmap = plt.get_cmap('YlOrRd')
    norm = plt.Normalize(vals.min(), vals.max())
    ax.bar(th, vals, width=np.radians(22.5 * 0.88),
           color=[cmap(norm(v)) for v in vals], edgecolor='white', linewidth=0.4,
           zorder=3)
    rmax = math.ceil(vals.max() / 50.0) * 50
    ax.set_ylim(0, rmax)
    ticks = np.arange(0, rmax + 1, 100)
    ax.set_yticks(ticks[1:])
    ax.set_yticklabels(['%d' % t for t in ticks[1:]], fontsize=6.8, color='#888888')
    ax.set_xticks(th)
    ax.set_xticklabels(DIR16, fontsize=7.2)
    ax.grid(color='#E2E2E2', lw=0.6)

    best = int(np.argmax(vals))
    ax.annotate('最优朝向 %s\n%.0f kWh/m²' % (DIR16[best], vals[best]),
                xy=(th[best], vals[best]), xytext=(th[best] + 0.30, rmax * 1.02),
                fontsize=8.6, color='#BE2F27', ha='center',
                arrowprops=dict(arrowstyle='->', color='#BE2F27', lw=1.0), zorder=7)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cax = fig.add_axes([0.715, 0.34, 0.016, 0.34])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label('kWh/m²·a', fontsize=7.6)
    cb.ax.tick_params(labelsize=6.8)

    P.caption(fig, 0.755, 0.30, [
        '垂直面全年接收辐射',
        '（含直射 + 散射 + 地面反射）',
        '',
        '水平面 %0.0f kWh/m²·a' % (GHI.sum() / 1000),
        '法向直射 %0.0f kWh/m²·a' % (DNI.sum() / 1000),
        '散射 %0.0f kWh/m²·a' % (DHI.sum() / 1000),
    ], fs=7.4, color='#444444')
    P.caption(fig, 0.085, 0.118, [
        '各朝向垂直面全年累计接收的太阳辐射（未考虑建筑遮挡），',
        '用于判断哪一朝向最值得争取被动得热 / 最需要遮阳。',
        '%s 向最高，%.0f kWh/m²·a。' % (DIR16[best], vals[best]),
    ], fs=7.4)
    P.header(fig, '太阳辐射玫瑰', 'Solar Radiation Rose · 16 朝向垂直面 · 全年累计')
    P.footer(fig, P.dateline('反射率取 0.2'))
    return P.save(fig, '01_极坐标玫瑰', '05_太阳辐射玫瑰.png')


if __name__ == '__main__':
    fig_annual()
    fig_monthly()
    fig_seasons()
    fig_prevailing()
    fig_rad_rose()
    print('--- 类型 1 完成 ---')
