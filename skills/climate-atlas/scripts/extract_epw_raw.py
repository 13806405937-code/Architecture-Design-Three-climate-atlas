# -*- coding: utf-8 -*-
"""extract_epw_raw —— EPW → data/epw_hourly.json（逐时原始值，不取整、不丢列）

与 climate_data.json 的分工：
  climate_data.json  已算好的统计量（月度/玫瑰/指标），画"统计类"图用它
  epw_hourly.json    逐时原值（含 sky_cover / opaque_cover 等 climate_data 未收的列），
                     画"逐时热图 / 散点 / 频次曲面"必须用它，否则会被取整抹平

用法
  python extract_epw_raw.py
  python extract_epw_raw.py --epw weather/xxx.epw
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_config as C      # noqa: E402
import epw_native as EN       # noqa: E402


def build(epw_path=None, out_path=None):
    epw_path = epw_path or C.EPW_PATH
    out_path = out_path or os.path.join(C.DATA, 'epw_hourly.json')
    if not os.path.isfile(epw_path):
        raise SystemExit('找不到 EPW：%s\n请改 atlas.json 的 "epw" 字段，或用 --epw 指定。' % epw_path)

    _loc, d = EN.read_epw(epw_path)
    out = {
        'source': os.path.basename(epw_path),
        'records': int(len(d['ta'])),
        'month': d['month'].astype(int).tolist(),
        'day': d['day'].astype(int).tolist(),
        'hour': (d['hour'].astype(int) - 1).tolist(),        # EPW 1–24 → 0–23
        'ta': d['ta'].tolist(),
        'tdew': d['tdew'].tolist(),
        'rh': d['rh'].tolist(),
        'ghi': d['ghi'].tolist(),
        'dni': d['dni'].tolist(),
        'dhi': d['dhi'].tolist(),
        'wind_dir': d['wind_dir'].tolist(),
        'wind_spd': d['wind_spd'].tolist(),
        'sky_cover': d['sky_cover'].tolist(),
        'opaque_cover': d['opaque_cover'].tolist(),
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))

    ws = d['wind_spd']
    print('records = %d' % out['records'])
    print('wind_spd: min %.2f max %.2f mean %.2f  unique=%d'
          % (ws.min(), ws.max(), ws.mean(), len(np.unique(ws))))
    print('sky_cover unique:', np.unique(d['sky_cover']))
    print('wind_dir == 0 (静风): %d' % int((d['wind_dir'] == 0).sum()))
    print('saved %s  %.0f KB' % (out_path, os.path.getsize(out_path) / 1024))
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description='EPW → epw_hourly.json')
    ap.add_argument('--epw', default=None, help='EPW 路径（默认取 atlas.json 的 epw 字段）')
    ap.add_argument('--out', default=None, help='输出 json（默认 <base>/data/epw_hourly.json）')
    a = ap.parse_args(argv)
    build(a.epw, a.out)


if __name__ == '__main__':
    main()
