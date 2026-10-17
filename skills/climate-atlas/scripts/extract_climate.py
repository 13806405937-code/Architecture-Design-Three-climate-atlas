# -*- coding: utf-8 -*-
"""extract_climate —— EPW → data/climate_data.json（后续所有图唯一的数据源）

两种引擎，产出的 JSON 结构完全一致：
  native   （默认）只用 numpy，零重依赖；太阳位置走 epw_native 的 NOAA 简化算法
  ladybug  需要 ladybug，太阳位置走 Sunpath，与 Ladybug Tools 生态逐位一致

用法
  python extract_climate.py                          # 用 atlas.json 里的 epw / data 目录
  python extract_climate.py --engine ladybug
  python extract_climate.py --epw weather/xxx.epw --out data/climate_data.json

口径说明（写进图注前请先读 references/metrics.md）
  日照可用小时  = DNI > 120 W/m²
  阴天          = 云量 ≥ 8（EPW 总云量十分制，ladybug 转 9 分制，阈值按 0–10 归一化）
  云量过半      = 云量 ≥ 5
  散射比        = ΣDHI / ΣGHI（比云量更可靠地反映阴晴）
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_config as C          # noqa: E402
import epw_native as EN           # noqa: E402

DIRS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
        'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
SPD_BINS = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 99.0]
SPD_LABELS = ['<1', '1-2', '2-3', '3-4', '4-5', '5-6', '>6']
CALM_LIMIT = 0.5          # m/s，静风判据
CLOUD_SCALE = 10.0        # EPW 总云量量纲上限（十分制）

CUM_DAYS = EN.CUM_DAYS


# ====================================================================== 读数据
def _read_native(epw_path):
    loc, d = EN.read_epw(epw_path)
    d['ws'], d['wd'] = d['wind_spd'], d['wind_dir']      # 统一键名
    d['cloud'] = d['sky_cover']                          # 总云量（十分制）
    # EPW 的 hour 是 1–24（时段末），统一成 0–23 —— 与 ladybug 的 datetime.hour
    # 以及 data/epw_hourly.json 的 hour 字段保持同一口径
    d['hour'] = d['hour'] - 1.0
    # 太阳位置按「0–23 整点」取值。
    # ⚠️ 不要用 hour±0.5 的中点：实测用整点与 ladybug 的差 ≤0.1°，
    #    用中点会整体偏 1 小时（正午前后高度角差 5–13°）。
    alt, azi = EN.solar_hourly(loc['latitude'], loc['longitude'], loc['time_zone'],
                               d['month'], d['day'], d['hour'])
    d['alt'], d['azi'] = alt, azi
    return loc, d, loc.get('ground_temperature', [])


def _read_ladybug(epw_path):
    try:
        from ladybug.epw import EPW
        from ladybug.sunpath import Sunpath
    except ImportError:
        raise SystemExit('--engine ladybug 需要 ladybug，请用 Ladybug Tools 自带的 python 运行，'
                         '或改用 --engine native')

    e = EPW(epw_path)
    lc = e.location
    loc = {'city': lc.city, 'country': lc.country, 'source': lc.source,
           'latitude': lc.latitude, 'longitude': lc.longitude,
           'time_zone': lc.time_zone, 'elevation': lc.elevation}

    dts = e.dry_bulb_temperature.datetimes
    d = {
        'month': np.array([x.month for x in dts], dtype=int),
        'day': np.array([x.day for x in dts], dtype=int),
        'hour': np.array([x.hour for x in dts], dtype=int),
        'ta': np.array(e.dry_bulb_temperature.values, dtype=float),
        'tdew': np.array(e.dew_point_temperature.values, dtype=float),
        'rh': np.array(e.relative_humidity.values, dtype=float),
        'ws': np.array(e.wind_speed.values, dtype=float),
        'wd': np.array(e.wind_direction.values, dtype=float),
        'ghi': np.array(e.global_horizontal_radiation.values, dtype=float),
        'dni': np.array(e.direct_normal_radiation.values, dtype=float),
        'dhi': np.array(e.diffuse_horizontal_radiation.values, dtype=float),
        'cloud': np.array(e.total_sky_cover.values, dtype=float),
        'precip': np.array(e.liquid_precipitation_depth.values, dtype=float),
    }
    n = len(d['ta'])
    sp = Sunpath(loc['latitude'], loc['longitude'], loc['time_zone'], 0.0)
    alt, azi = np.zeros(n), np.zeros(n)
    for h in range(n):
        s = sp.calculate_sun_from_hoy(h)
        alt[h], azi[h] = s.altitude, s.azimuth
    d['alt'], d['azi'] = alt, azi
    return loc, d, _ground_from_header(epw_path)


def _ground_from_header(epw_path):
    """EPW 文件头 GROUND TEMPERATURES（对地下空间 / 地道风有直接价值）"""
    try:
        with open(epw_path, 'r', encoding='utf-8', errors='replace') as f:
            head = [f.readline() for _ in range(8)]
    except OSError:
        return []
    return EN._parse_ground(head)


# ====================================================================== 统计
def _m_mean(a, mon):
    return [round(float(np.mean(a[mon == m])), 2) for m in range(1, 13)]


def _m_max(a, mon):
    return [round(float(np.max(a[mon == m])), 2) for m in range(1, 13)]


def _m_min(a, mon):
    return [round(float(np.min(a[mon == m])), 2) for m in range(1, 13)]


def _m_sum(a, mon):
    return [round(float(np.sum(a[mon == m])), 1) for m in range(1, 13)]


def _m_count(cond, mon):
    return [int(np.sum(cond & (mon == m))) for m in range(1, 13)]


def _m_pct(cond, mon):
    return [round(100.0 * float(np.sum(cond & (mon == m))) / max(1, int(np.sum(mon == m))), 1)
            for m in range(1, 13)]


def wind_rose(ws, wd, mask=None):
    """16 方位 × 风速分档的小时数矩阵"""
    n = len(ws)
    if mask is None:
        mask = np.ones(n, dtype=bool)
    w_s, w_d = ws[mask], wd[mask]
    calm = int(np.sum(w_s < CALM_LIMIT))
    mat = np.zeros((len(DIRS), len(SPD_LABELS)), dtype=int)
    sel = w_s >= CALM_LIMIT
    for d, s in zip(w_d[sel], w_s[sel]):
        di = int(((d + 11.25) % 360.0) / 22.5) % 16
        si = int(np.digitize(s, SPD_BINS)) - 1
        si = min(max(si, 0), len(SPD_LABELS) - 1)
        mat[di, si] += 1
    tot = int(mask.sum())

    # 各方位平均风速（仅该方位非静风样本）
    mean_by_dir = []
    for i in range(16):
        lo, hi = i * 22.5 - 11.25, i * 22.5 + 11.25
        ang = (w_d - lo) % 360.0
        sel_d = (ang < 22.5) & sel
        mean_by_dir.append(round(float(np.mean(w_s[sel_d])), 2) if sel_d.any() else 0.0)

    return {
        'directions': DIRS,
        'speed_labels': SPD_LABELS,
        'matrix': mat.tolist(),
        'total_hours': tot,
        'calm_hours': calm,
        'calm_pct': round(100.0 * calm / tot, 1) if tot else 0.0,
        'dir_pct': [round(100.0 * mat[i].sum() / tot, 2) if tot else 0.0 for i in range(16)],
        'mean_speed_by_dir': mean_by_dir,
        'mean_speed': round(float(np.mean(w_s)), 2) if tot else 0.0,
    }


def _dominant(wr):
    p = wr['dir_pct']
    i = int(np.argmax(p))
    return DIRS[i], p[i]


def _month_dominant(ws, wd, mon):
    out = []
    for m in range(1, 13):
        mm = mon == m
        w_s, w_d = ws[mm], wd[mm]
        cnt = np.zeros(16)
        sel = w_s >= CALM_LIMIT
        for d in w_d[sel]:
            cnt[int(((d + 11.25) % 360.0) / 22.5) % 16] += 1
        out.append(DIRS[int(np.argmax(cnt))] if cnt.any() else '—')
    return out


# ====================================================================== 组装
def assemble(loc, d, ground, epw_path, engine):
    mon, day, hour = d['month'], d['day'], d['hour']
    ta, tdew, rh = d['ta'], d['tdew'], d['rh']
    ws, wd = d['ws'], d['wd']
    ghi, dni, dhi = d['ghi'], d['dni'], d['dhi']
    cloud, precip = d['cloud'], d['precip']
    n = len(ta)

    days_in_month = [round(int(np.sum(mon == m)) / 24.0, 2) for m in range(1, 13)]

    sunshine = dni > 120.0                 # 直射可用小时
    overcast = cloud >= 0.8 * CLOUD_SCALE  # 阴天
    cloudy_half = cloud >= 0.5 * CLOUD_SCALE

    masks = {
        'annual': None,
        'summer': np.isin(mon, [6, 7, 8]),
        'winter': np.isin(mon, [12, 1, 2]),
        'spring': np.isin(mon, [3, 4, 5]),
        'autumn': np.isin(mon, [9, 10, 11]),
    }
    wr = {k: wind_rose(ws, wd, v) for k, v in masks.items()}

    # ---------- 太阳轨迹（每月 21 日） ----------
    lat, lon, tz = loc['latitude'], loc['longitude'], loc['time_zone']
    arcs = []
    for m in range(1, 13):
        idx = np.where((mon == m) & (day == 21))[0]
        pts = []
        for i in idx:
            if d['alt'][i] > 0:
                pts.append([int(hour[i]), round(float(d['alt'][i]), 2),
                            round(float(d['azi'][i]), 2)])
        doy21 = int(CUM_DAYS[m - 1]) + 21
        rise, set_ = EN.sunrise_sunset(doy21, lat, lon, tz)
        arcs.append({'month': m, 'points': pts,
                     'sunrise': round(rise, 2), 'sunset': round(set_, 2),
                     'daylength': round(set_ - rise, 2)})

    # ---------- 月度集合 ----------
    monthly = {
        'days': days_in_month,
        'ta_mean': _m_mean(ta, mon), 'ta_max': _m_max(ta, mon), 'ta_min': _m_min(ta, mon),
        'tdew_mean': _m_mean(tdew, mon),
        'rh_mean': _m_mean(rh, mon),
        'ws_mean': _m_mean(ws, mon),
        'ghi_total': _m_sum(ghi, mon),      # Wh/m²
        'dni_total': _m_sum(dni, mon),
        'dhi_total': _m_sum(dhi, mon),
        'sunshine_hours': _m_count(sunshine, mon),
        'overcast_hours': _m_count(overcast, mon),
        'overcast_days': [round(c / 24.0, 1) for c in _m_count(overcast, mon)],
        'cloud_mean': _m_mean(cloud, mon),
        'cloud_gt50_pct': _m_pct(cloudy_half, mon),
        'diffuse_ratio': [
            round(float(np.sum(dhi[mon == m]) / max(1.0, np.sum(ghi[mon == m]))), 3)
            for m in range(1, 13)],
    }

    # ---------- 气候设计指标 ----------
    def pct(cond):
        return round(100.0 * float(np.sum(cond)) / n, 1)

    comfort = (ta >= 18.0) & (ta <= 26.0) & (rh >= 30.0) & (rh <= 70.0)
    natvent = (ta <= 26.0) & (tdew <= 20.0) & (ta >= 12.0)
    heating = ta < 12.0
    cooling = ta > 26.0
    dehumid = tdew > 20.0
    hot_humid = (ta > 26.0) & (tdew > 20.0)

    monthly['comfort_pct'] = _m_pct(comfort, mon)
    monthly['natvent_pct'] = _m_pct(natvent, mon)
    monthly['heating_pct'] = _m_pct(heating, mon)
    monthly['cooling_pct'] = _m_pct(cooling, mon)

    indicators = {
        'engine': engine,
        'hours_total': n,
        'comfort_hours': int(comfort.sum()), 'comfort_pct': pct(comfort),
        'natural_vent_hours': int(natvent.sum()), 'natural_vent_pct': pct(natvent),
        'heating_hours': int(heating.sum()), 'heating_pct': pct(heating),
        'cooling_hours': int(cooling.sum()), 'cooling_pct': pct(cooling),
        'hot_humid_hours': int(hot_humid.sum()), 'hot_humid_pct': pct(hot_humid),
        'dehumid_hours': int(dehumid.sum()), 'dehumid_pct': pct(dehumid),
        'sunshine_hours_year': int(sunshine.sum()),
        'mean_ta': round(float(ta.mean()), 2),
        'mean_ws': round(float(ws.mean()), 2),
        'gha_total_kwh_m2': round(float(ghi.sum()) / 1000.0, 1),
        'dni_total_kwh_m2': round(float(dni.sum()) / 1000.0, 1),
        'hdd18': round(float(np.sum(np.maximum(18.0 - ta, 0.0))) / 24.0, 1),
        'cdd26': round(float(np.sum(np.maximum(ta - 26.0, 0.0))) / 24.0, 1),
        'cloud_mean_pct': round(float(cloud.mean()) / CLOUD_SCALE * 100.0, 1),
        'rh_mean': round(float(rh.mean()), 1),
    }

    out = {
        'meta': {
            'epw': os.path.basename(epw_path),
            'engine': engine,
            'city': loc['city'], 'country': loc['country'],
            'wmo': loc.get('wmo', ''),
            'latitude': round(float(loc['latitude']), 3),
            'longitude': round(float(loc['longitude']), 3),
            'time_zone': loc['time_zone'],
            'elevation': round(float(loc['elevation']), 1),
            'source': loc.get('source', ''), 'records': n,
        },
        'monthly': monthly,
        'month_dominant_wind': _month_dominant(ws, wd, mon),
        'windrose': wr,
        'sunpath': {
            'latitude': round(float(lat), 3), 'longitude': round(float(lon), 3),
            'arcs': arcs,
            'altitude_hourly': [round(float(v), 2) for v in d['alt']],
            'azimuth_hourly': [round(float(v), 2) for v in d['azi']],
        },
        'psychro': {
            'ta': [round(float(v), 1) for v in ta],
            'tdew': [round(float(v), 1) for v in tdew],
            'rh': [round(float(v), 0) for v in rh],
        },
        'ground_temperature': ground,
        'indicators': indicators,
        'hourly': {
            'month': mon.tolist(), 'day': day.tolist(), 'hour': hour.tolist(),
            'ta': [round(float(v), 1) for v in ta],
            'tdew': [round(float(v), 1) for v in tdew],
            'rh': [round(float(v), 0) for v in rh],
            'ws': [round(float(v), 2) for v in ws],
            'wd': [round(float(v), 0) for v in wd],
            'ghi': [round(float(v), 1) for v in ghi],
            'dni': [round(float(v), 1) for v in dni],
            'dhi': [round(float(v), 1) for v in dhi],
            'cloud': [round(float(v), 0) for v in cloud],
            'precip': [round(float(v), 2) for v in precip],
        },
    }
    return out


# ====================================================================== 主流程
def build(epw_path=None, out_path=None, engine='native'):
    epw_path = epw_path or C.EPW_PATH
    out_path = out_path or os.path.join(C.DATA, 'climate_data.json')
    if not os.path.isfile(epw_path):
        raise SystemExit('找不到 EPW：%s\n请在 atlas.json 里改 "epw" 字段，或用 --epw 指定。' % epw_path)

    loc, d, ground = (_read_ladybug if engine == 'ladybug' else _read_native)(epw_path)
    out = assemble(loc, d, ground, epw_path, engine)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False)

    mo, ind = out['monthly'], out['indicators']
    print('meta :', json.dumps(out['meta'], ensure_ascii=False))
    print()
    print('=== 月度均温 / 露点 / RH ===')
    print('  月  :', list(range(1, 13)))
    print('  均温:', mo['ta_mean'])
    print('  露点:', mo['tdew_mean'])
    print('  RH  :', mo['rh_mean'])
    print()
    print('=== 月度太阳辐射 (kWh/m²) ===')
    print('  GHI :', [round(v / 1000, 1) for v in mo['ghi_total']])
    print('  DNI :', [round(v / 1000, 1) for v in mo['dni_total']])
    print('  直射可用小时:', mo['sunshine_hours'])
    print()
    print('=== 风环境 ===')
    for k, lab in (('annual', '全年'), ('summer', '夏季'), ('winter', '冬季')):
        w = out['windrose'][k]
        print('  %s: 均风速 %.2f m/s  主导 %s  静风 %.1f%%'
              % (lab, w['mean_speed'], _dominant(w), w['calm_pct']))
    print('  逐月主导风向:', out['month_dominant_wind'])
    print()
    print('=== 气候指标 ===')
    for k, v in ind.items():
        print('  %-22s %s' % (k, v))
    print()
    print('written ->', out_path, os.path.getsize(out_path) // 1024, 'KB')
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description='EPW → climate_data.json')
    ap.add_argument('--epw', default=None, help='EPW 路径（默认取 atlas.json 的 epw 字段）')
    ap.add_argument('--out', default=None, help='输出 json（默认 <base>/data/climate_data.json）')
    ap.add_argument('--engine', choices=['native', 'ladybug'], default='native')
    a = ap.parse_args(argv)
    build(a.epw, a.out, a.engine)


if __name__ == '__main__':
    main()
