# -*- coding: utf-8 -*-
"""epw_native —— 不依赖 ladybug 的 EPW 读取 + 太阳位置

为什么要有这个：本技能要能在只装了 numpy 的机器上跑。
ladybug 仍是"标准答案"（与 LBT 生态一致），本模块是零依赖替身。

与 ladybug 实测对照（上海 CSWD 583620，8760 h）：
    高度角  |Δ| max 0.91°  mean 0.18°
    方位角  |Δ| max 1.10°  mean 0.24°
    「太阳在地平线上」小时数 4432 → 4388（阈值 alt>2.29° 时 4221 → 4205，差 0.4%）
差异来自 NOAA 简化算法（忽略大气折射与非球形地球），量级远小于模型本身的不确定度，
但若论文/报审需要与 Ladybug 逐位对齐，请用 --engine ladybug。
"""
import math

import numpy as np

# EPW 数据列（0-based，跳过 8 行文件头）
COL = {
    'year': 0, 'month': 1, 'day': 2, 'hour': 3, 'minute': 4,
    'ta': 6, 'tdew': 7, 'rh': 8, 'pressure': 9,
    'ghi': 13, 'dni': 14, 'dhi': 15,
    'wind_dir': 20, 'wind_spd': 21,
    'sky_cover': 22, 'opaque_cover': 23,
    'precip': 33,
}

CUM_DAYS = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], dtype=int)


def read_epw(path):
    """读 EPW → (location dict, data dict)

    ⚠️ LOCATION 行是 10 个字段：LOCATION,city,state,country,source,WMO,lat,lon,tz,elev
       少有人注意到 state 也在里面，所以 lat 在索引 6 而不是 5 —— 差一位会把纬度读成 WMO 号，
       太阳位置全错（本项目踩过）。
    """
    loc = {'city': '', 'state': '', 'country': '', 'source': '', 'wmo': '',
           'latitude': 0.0, 'longitude': 0.0, 'time_zone': 0.0, 'elevation': 0.0}
    rows = []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        head = [f.readline() for _ in range(8)]
        first = [x.strip() for x in head[0].strip().split(',')]

        def num(i, dflt):
            try:
                return float(first[i])
            except (IndexError, TypeError, ValueError):
                return dflt

        if first and first[0].upper().startswith('LOCATION'):
            loc.update({
                'city': first[1] if len(first) > 1 else '',
                'state': first[2] if len(first) > 2 else '',
                'country': first[3] if len(first) > 3 else '',
                'source': first[4] if len(first) > 4 else '',
                'wmo': first[5] if len(first) > 5 else '',
                'latitude': num(6, 0.0),
                'longitude': num(7, 0.0),
                'time_zone': num(8, 0.0),
                'elevation': num(9, 0.0),
            })
        for line in f:
            if not line.strip():
                continue
            p = line.split(',')
            if len(p) < 24:
                continue
            rows.append(p)
    loc['ground_temperature'] = _parse_ground(head)
    loc['header'] = [h.rstrip('\n') for h in head]

    data = {}
    for key, i in COL.items():
        data[key] = np.array([float(r[i]) for r in rows])
    return loc, data


def _parse_ground(head):
    """EPW 文件头 GROUND TEMPERATURES（对地下空间 / 地道风有直接价值）"""
    out = []
    for ln in head:
        if not ln.startswith('GROUND TEMPERATURES'):
            continue
        parts = ln.strip().split(',')
        body = parts[2:]
        for g in range(len(body) // 16):
            grp = body[g * 16:(g + 1) * 16]
            try:
                depth = float(grp[0])
            except (TypeError, ValueError):
                continue
            seg = [float(v) for v in grp[4:16] if v.strip() != '']
            if len(seg) == 12:
                out.append({'depth_m': depth, 'temp': [round(v, 2) for v in seg]})
    return out


def solar_position(lat, lon, tz, doy, hour_frac):
    """NOAA 简化算法。返回 (altitude_deg, azimuth_deg 自北顺时针)"""
    gamma = 2.0 * math.pi / 365.0 * (doy - 1 + (hour_frac - 12.0) / 24.0)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.001480 * math.sin(3 * gamma))
    tst = hour_frac * 60.0 + eqtime + 4.0 * lon - 60.0 * tz
    ha = math.radians(tst / 4.0 - 180.0)
    phi = math.radians(lat)
    e = -math.cos(decl) * math.sin(ha)
    n = math.cos(phi) * math.sin(decl) - math.sin(phi) * math.cos(decl) * math.cos(ha)
    u = math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(ha)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, u))))
    azi = math.degrees(math.atan2(e, n)) % 360.0
    return alt, azi


def solar_hourly(lat, lon, tz, month, day, hour):
    """逐时太阳位置（向量化的 python 循环，8760 条约 0.4 s）"""
    doy = CUM_DAYS[np.asarray(month, dtype=int) - 1] + np.asarray(day, dtype=int)
    n = len(doy)
    alt = np.zeros(n)
    azi = np.zeros(n)
    for i in range(n):
        alt[i], azi[i] = solar_position(lat, lon, tz, int(doy[i]), float(hour[i]))
    return alt, azi


def sunrise_sunset(doy, lat, lon, tz):
    """解析法日出/日落（-0.833° 折射修正 + 经度时差），返回地方标准时（小时）"""
    phi = math.radians(lat)
    B = 2.0 * math.pi * (doy - 1) / 365.0
    dec = (0.006918 - 0.399912 * math.cos(B) + 0.070257 * math.sin(B)
           - 0.006758 * math.cos(2 * B) + 0.000907 * math.sin(2 * B)
           - 0.002697 * math.cos(3 * B) + 0.001480 * math.sin(3 * B))
    cosw = ((math.sin(math.radians(-0.833)) - math.sin(phi) * math.sin(dec)) /
            (math.cos(phi) * math.cos(dec)))
    cosw = max(-1.0, min(1.0, cosw))
    w = math.degrees(math.acos(cosw))
    solar_noon = 12.0 - (lon - tz * 15.0) * 4.0 / 60.0
    return solar_noon - w / 15.0, solar_noon + w / 15.0
