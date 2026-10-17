# -*- coding: utf-8 -*-
"""run_solar_site —— 场地日照时数网格（含建筑遮挡），全年 + 四季一次算完

产出 data/sunhours_grid.json：
  coords        未被建筑占压的网格点 (x, y)
  hours_year    每个点全年受照小时
  hours_summer / hours_winter / hours_spring / hours_autumn
  season_hours  各季节"可照时数"分母（太阳在地平线以上的小时数）

用法
  python run_solar_site.py                 # 步长取 atlas.json 的 site.step
  python run_solar_site.py --step 4        # 粗网格快速试跑
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_config as C      # noqa: E402
import climate_engine as E    # noqa: E402


def build(step=None, out_path=None):
    step = float(step or C.SITE.get('step', 2.0))
    out_path = out_path or os.path.join(C.DATA, 'sunhours_grid.json')
    x0, y0 = float(C.SITE['xmin']), float(C.SITE['ymin'])
    x1, y1 = float(C.SITE['xmax']), float(C.SITE['ymax'])

    t_all = time.time()
    cd = E.load_climate()
    objs = E.load_building()
    tris, _owner = E.all_triangles(objs)
    hf, cell = E.build_heightfield(tris, cell=float(C.SITE.get('cell', 1.0)), zmax=40.0)
    print('building objects=%d triangles=%d heightfield max=%.2f m'
          % (len(objs), len(tris), hf.max()))

    alt = np.array(cd['sunpath']['altitude_hourly'], dtype=float)
    azi = np.array(cd['sunpath']['azimuth_hourly'], dtype=float)
    dirs = E.sun_dirs(alt, azi)
    mon = np.array(cd['hourly']['month'], dtype=int)

    up = E.sun_up(dirs)
    print('sun-up hours = %d (阈值 z > %.3f)' % (up.sum(), C.SUNUP_ZMIN))

    xs = np.arange(x0 + step / 2, x1, step)
    ys = np.arange(y0 + step / 2, y1, step)
    GX, GY = np.meshgrid(xs, ys)
    PX = GX.ravel().astype(np.float32)
    PY = GY.ravel().astype(np.float32)

    ii = np.clip(((PX - x0) / cell).astype(int), 0, hf.shape[1] - 1)
    jj = np.clip(((PY - y0) / cell).astype(int), 0, hf.shape[0] - 1)
    on_bldg = hf[jj, ii] > 0.5
    print('grid points = %d   on building = %d' % (PX.size, int(on_bldg.sum())))

    sel = ~on_bldg
    PZ = np.zeros(int(sel.sum()), dtype=np.float32)

    t0 = time.time()
    lit = E.sunlit(PX[sel], PY[sel], PZ, dirs[up], hf, cell=cell,
                   step=step, zmax=30.0, xmin=x0, ymin=y0)
    print('sunlit computed in %.1f s   shape=%s' % (time.time() - t0, lit.shape))

    m_up = mon[up]
    seasons = {
        'year': np.ones_like(m_up, dtype=bool),
        'summer': np.isin(m_up, [6, 7, 8]),
        'winter': np.isin(m_up, [12, 1, 2]),
        'spring': np.isin(m_up, [3, 4, 5]),
        'autumn': np.isin(m_up, [9, 10, 11]),
    }
    out = {
        'step': step,
        'xs': xs.tolist(),
        'ys': ys.tolist(),
        'n_total_points': int(PX.size),
        'on_building_count': int(on_bldg.sum()),
        'sun_up_hours': int(up.sum()),
        'season_hours': {k: int(v.sum()) for k, v in seasons.items()},
        'coords': np.stack([PX[sel], PY[sel]], axis=1).round(2).tolist(),
    }
    for k, m in seasons.items():
        out['hours_' + k] = lit[:, m].sum(axis=1).astype(int).tolist()

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))

    arr = np.array(out['hours_year'], dtype=float)
    print('saved %s (%.1f KB)  total %.1f s'
          % (out_path, os.path.getsize(out_path) / 1024, time.time() - t_all))
    print('year sunlit hours: min=%.0f p25=%.0f median=%.0f p75=%.0f max=%.0f  / 可照 %d'
          % (arr.min(), np.percentile(arr, 25), np.median(arr),
             np.percentile(arr, 75), arr.max(), out['season_hours']['year']))
    return out_path


def main(argv=None):
    ap = argparse.ArgumentParser(description='场地日照时数网格（含遮挡）')
    ap.add_argument('--step', type=float, default=None, help='网格步长 m（默认取 atlas.json）')
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    build(a.step, a.out)


if __name__ == '__main__':
    main()
