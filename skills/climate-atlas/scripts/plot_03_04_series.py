# -*- coding: utf-8 -*-
"""类型 3 · 逐时热图  |  类型 4 · 月度图表

逐时热图：X = 一天中的钟点，Y = 一年中的日期，颜色 = 参数值
月度图表：X = 月份
数据源：data/epw_hourly.json（EPW 原始逐时值，不取整）
"""
import json
import os

import numpy as np
import matplotlib.pyplot as plt

import plot_common as P

BASE = P.BASE
with open(os.path.join(BASE, 'data', 'epw_hourly.json'), encoding='utf-8') as f:
    R = json.load(f)
CD = P.load_climate()

MON = np.array(R['month'], dtype=int)
DAY = np.array(R['day'], dtype=int)
HOUR = np.array(R['hour'], dtype=int)          # 0-23
CUM = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
DOY = CUM[MON - 1] + DAY

TA = np.array(R['ta'], dtype=float)
TDEW = np.array(R['tdew'], dtype=float)
RH = np.array(R['rh'], dtype=float)
WS = np.array(R['wind_spd'], dtype=float)
WD = np.array(R['wind_dir'], dtype=float)
GHI = np.array(R['ghi'], dtype=float)
DNI = np.array(R['dni'], dtype=float)
DHI = np.array(R['dhi'], dtype=float)
SKY = np.array(R['sky_cover'], dtype=float)

M = np.arange(1, 13)
MLAB = ['%d月' % m for m in M]
MONTH_START = CUM


def to_grid(vals):
    g = np.full((365, 24), np.nan)
    g[DOY - 1, HOUR] = vals
    return g


def mstat(vals, how):
    out = []
    for m in M:
        v = vals[MON == m]
        out.append(float(np.mean(v)) if how == 'mean' else float(np.sum(v)))
    return np.array(out)


def style_year_axis(ax, ylab=True, fs=7.4):
    ax.set_xlim(0, 24)
    ax.set_ylim(1, 366)
    ax.set_xticks([0, 4, 8, 12, 16, 20, 24])
    ax.set_xticklabels(['0', '4', '8', '12', '16', '20', '24'], fontsize=fs)
    ax.set_yticks(MONTH_START + 15)
    ax.set_yticklabels(['%d' % m for m in M] if ylab else [''] * 12, fontsize=fs)
    ax.set_xlabel('钟点 (h)', fontsize=fs)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_color('#BBBBBB')
        s.set_linewidth(0.7)


# ================================================================== 类型 3
HEAT_PARAMS = [
    ('干球温度', 'Dry Bulb Temperature', TA, 'RdYlBu_r', '°C', 0, 36),
    ('露点温度', 'Dew Point Temperature', TDEW, 'RdYlBu_r', '°C', -12, 28),
    ('相对湿度', 'Relative Humidity', RH, 'YlGnBu', '%', 20, 100),
    ('风速', 'Wind Speed', WS, 'Blues', 'm/s', 0, 9),
    ('太阳总辐射', 'Global Horizontal Radiation', GHI, 'YlOrRd', 'Wh/m²', 0, 950),
    ('法向直射辐射', 'Direct Normal Radiation', DNI, 'YlOrRd', 'Wh/m²', 0, 800),
]


def fig_hourly_heatmap():
    fig = plt.figure(figsize=(11.0, 13.8))
    y0, step, hgt = 0.818, 0.131, 0.104
    for i, (cn, en, vals, cmap, unit, vmin, vmax) in enumerate(HEAT_PARAMS):
        ax = fig.add_axes([0.075, y0 - i * step, 0.775, hgt])
        g = to_grid(vals)
        im = ax.imshow(g, aspect='auto', origin='lower',
                       extent=[0, 24, 1, 366], cmap=cmap,
                       vmin=vmin, vmax=vmax, interpolation='nearest')
        style_year_axis(ax, ylab=(i % 2 == 0))
        ax.set_title('%s   %s' % (cn, en), fontsize=9.6, color='#222222',
                     loc='left', pad=3)
        cax = fig.add_axes([0.862, y0 - i * step + 0.012, 0.011, hgt - 0.024])
        cb = fig.colorbar(im, cax=cax)
        cb.ax.tick_params(labelsize=6.4)
        cb.set_label(unit, fontsize=6.4)

    P.header(fig, '逐时气象参数热图',
             'Hourly Climate Heatmaps · X = 钟点 / Y = 一年中的日期 / 颜色 = 参数值')
    _day = (HOUR >= 9) & (HOUR <= 17)
    _nit = (HOUR <= 5)
    _i_hi = int(np.argmax(TA))
    _i_lo = int(np.argmin(TA))
    P.caption(fig, 0.075, 0.048, [
        '读图要点',
        '温度：峰值 %0.1f °C（%d 月 %d 日 %d 时）、最低 %0.1f °C（%d 月 %d 日 %d 时），'
        '年较差约 %0.0f K。'
        % (TA[_i_hi], MON[_i_hi], DAY[_i_hi], HOUR[_i_hi],
           TA[_i_lo], MON[_i_lo], DAY[_i_lo], HOUR[_i_lo], TA.max() - TA.min()),
        '露点：与温度同步起伏，露点 > 20 °C 的小时占全年 %0.1f%%。'
        % (100.0 * float((TDEW > 20).mean())),
        '湿度：整体与温度反相，夜间至清晨偏湿。',
        '风速：日间（9–17 时）均 %0.2f m/s、夜间（0–5 时）均 %0.2f m/s；EPW 源值本身为整数级。'
        % (WS[_day].mean(), WS[_nit].mean()),
        '辐射：呈"日—年"双周期条带；正午 GHI 全年最高 %0.0f Wh/m²。' % GHI.max(),
    ], fs=7.2, color='#444444')
    P.footer(fig, P.dateline('原始逐时值'))
    return P.save(fig, '03_逐时热图', '01_逐时热图矩阵_六参数.png')


# ================================================================== 类型 4
def fig_monthly_chart():
    fig = plt.figure(figsize=(11.0, 13.8))
    ax = [fig.add_axes([0.085, 0.812 - i * 0.134, 0.795, 0.096]) for i in range(6)]
    x = M

    ta_mean = mstat(TA, 'mean')
    ta_max = np.array([TA[MON == m].max() for m in M])
    ta_min = np.array([TA[MON == m].min() for m in M])
    tdew_mean = mstat(TDEW, 'mean')
    rh_mean = mstat(RH, 'mean')
    ws_mean = mstat(WS, 'mean')
    ghi_m = mstat(GHI, 'sum') / 1000.0
    dni_m = mstat(DNI, 'sum') / 1000.0
    dhi_m = mstat(DHI, 'sum') / 1000.0
    sky_mean = mstat(SKY, 'mean')
    cloudy_pct = np.array([(SKY[MON == m] >= 5).mean() * 100 for m in M])

    # 1 干球温度
    a = ax[0]
    a.fill_between(x, ta_min, ta_max, color='#F2C4B0', alpha=0.8,
                   label='月极值区间', zorder=2)
    a.plot(x, ta_mean, '-o', color='#C1553B', lw=1.6, ms=3.4, label='月均', zorder=3)
    for xi, v in zip(x, ta_mean):
        a.text(xi, ta_max[xi - 1] + 1.4, '%.1f' % v, ha='center', fontsize=5.8,
               color='#8A3A22')
    a.set_ylabel('°C', fontsize=7.4)
    a.set_ylim(-8, 40)
    a.legend(loc='upper right', fontsize=6.4, ncol=2)
    a.set_title('干球温度   Dry Bulb Temperature', fontsize=9.6, loc='left', pad=3)

    # 2 露点 + 相对湿度
    a = ax[1]
    a.plot(x, tdew_mean, '-o', color='#4E8C8C', lw=1.6, ms=3.4, label='月均露点')
    a.axhline(20, color='#C0392B', lw=0.9, ls='--')
    a.text(12.55, 20, '露点 20 °C 除湿阈值', fontsize=6.0, color='#C0392B',
           va='bottom', ha='right')
    a.set_ylabel('°C', fontsize=7.4)
    a.set_ylim(-2, 28)
    a2 = a.twinx()
    a2.plot(x, rh_mean, '-s', color='#7B9EC4', lw=1.4, ms=3.0, label='月均相对湿度')
    a2.set_ylabel('%', fontsize=7.4)
    a2.set_ylim(60, 90)
    a2.grid(False)
    a.legend(loc='lower right', fontsize=6.4)
    a2.legend(loc='upper right', fontsize=6.4)
    a.set_title('露点温度 与 相对湿度   Dew Point & Relative Humidity',
                fontsize=9.6, loc='left', pad=3)

    # 3 太阳辐射构成
    a = ax[2]
    a.bar(x, dhi_m, color='#CFE3F5', label='散射 DHI', zorder=2)
    a.bar(x, dni_m, bottom=dhi_m, color='#EFA135', label='直射 DNI', zorder=2)
    a.plot(x, ghi_m, '-o', color='#C0392B', lw=1.3, ms=3.0,
           label='水平面总量 GHI', zorder=3)
    a.set_ylabel('kWh/m²·月', fontsize=7.2)
    a.set_ylim(0, 200)
    a.legend(loc='upper right', fontsize=6.4, ncol=3)
    a.set_title('太阳辐射构成   Solar Radiation Composition', fontsize=9.6,
                loc='left', pad=3)

    # 4 风速
    a = ax[3]
    a.bar(x, ws_mean, color='#5F7A99', width=0.65, zorder=2, label='月均风速')
    for xi, v in zip(x, ws_mean):
        a.text(xi, v + 0.09, '%.1f' % v, ha='center', fontsize=6.0, color='#445566')
    a.set_ylabel('m/s', fontsize=7.4)
    a.set_ylim(0, 4.8)
    a.legend(loc='upper right', fontsize=6.4)
    a.set_title('风速   Wind Speed（月均，全年 %0.2f m/s）' % WS.mean(),
                fontsize=9.6, loc='left', pad=3)

    # 5 云量
    a = ax[4]
    a.bar(x, sky_mean, color='#B9B9B9', width=0.65, label='月均云量 (okta)')
    a.set_ylabel('okta', fontsize=7.4)
    a.set_ylim(0, 6)
    a2 = a.twinx()
    a2.plot(x, cloudy_pct, '-o', color='#6E6E6E', lw=1.3, ms=3.0,
            label='云量 ≥5 okta 小时占比')
    a2.set_ylabel('%', fontsize=7.4)
    a2.set_ylim(0, 60)
    a2.grid(False)
    a.legend(loc='lower left', fontsize=6.4)
    a2.legend(loc='upper right', fontsize=6.4)
    a.set_title('云量   Cloud Cover (okta 0–9)', fontsize=9.6, loc='left', pad=3)

    # 6 被动策略时段占比
    a = ax[5]
    mo = CD['monthly']
    comf = np.array(mo['comfort_pct'], float)
    natv = np.array(mo['natvent_pct'], float)
    heat = np.array(mo['heating_pct'], float)
    cool = np.array(mo['cooling_pct'], float)
    a.bar(x, heat, color='#5B8DB8', label='需供暖')
    a.bar(x, cool, bottom=heat, color='#C1553B', label='需制冷')
    a.bar(x, natv, bottom=heat + cool, color='#8FBF6A', label='自然通风可用')
    a.bar(x, comf, bottom=heat + cool + natv, color='#F5D98B', label='舒适区间')
    a.set_ylabel('占比 %', fontsize=7.4)
    a.set_ylim(0, 108)
    a.legend(loc='upper center', fontsize=6.6, ncol=4, bbox_to_anchor=(0.5, -0.26))
    a.set_title('被动策略时段占比   Passive Strategy Hours', fontsize=9.6,
                loc='left', pad=3)

    for i, a in enumerate(ax):
        a.set_xticks(x)
        a.set_xticklabels(MLAB if i == 5 else [''] * 12, fontsize=7.2)
        a.set_xlim(0.3, 12.7)
        a.grid(axis='y', color='#EAEAEA', lw=0.7)
        a.set_axisbelow(True)

    P.header(fig, '月度气候图表',
             'Monthly Climate Charts · 12 个月 · 温度 / 湿度 / 辐射 / 风 / 云量 / 被动策略')
    P.footer(fig, P.dateline('原始逐时值统计'))
    return P.save(fig, '04_月度图表', '01_月度图表_六联.png')


if __name__ == '__main__':
    fig_hourly_heatmap()
    fig_monthly_chart()
    print('--- 类型 3 / 4 完成 ---')
