# -*- coding: utf-8 -*-
"""run_all —— 一条命令跑完整套图集

    python run_all.py                 # 数据 + 全部 7 类图
    python run_all.py --skip-data     # 数据已生成，只重画图
    python run_all.py --only 01,06    # 只跑指定类型
    python run_all.py --engine ladybug

阶段划分
    data : extract_climate → extract_epw_raw → run_solar_site
    00   : 总图版（依赖 06 的 sunhours 与 meshh）
    01   : 极坐标玫瑰族
    02   : 太阳轨迹族（依赖 mesh + sunhours）
    03   : 逐时热图族
    04   : 月度图表族
    05   : 三维曲面族
    06   : 建筑专题族（依赖 mesh + sunhours）
    99   : 图集总览（必须在最后）
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import atlas_config as C          # noqa: E402

STAGES = {
    '01': 'plot_01_polar.py',
    '02': 'plot_02_05_sun.py',      # 02 + 05 同脚本
    '03': 'plot_03_04_series.py',   # 03 + 04 同脚本
    '06': 'plot_06_building.py',
    '00': 'plot_00_overview.py',
    '99': 'plot_99_index.py',
}
DATA_ORDER = ['extract_climate.py', 'extract_epw_raw.py', 'run_solar_site.py']
PLOT_ORDER = ['01', '03', '02', '06', '00', '99']


def run(script, args=()):
    path = os.path.join(HERE, script)
    t0 = time.time()
    print('\n>>> %s' % script, flush=True)
    r = subprocess.run([sys.executable, path] + list(args))
    if r.returncode != 0:
        raise SystemExit('%s 失败（exit %d）' % (script, r.returncode))
    print('<<< %s  %.1f s' % (script, time.time() - t0), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description='一键生成气候分析图集')
    ap.add_argument('--skip-data', action='store_true', help='跳过数据提取，直接出图')
    ap.add_argument('--only', default='', help='只跑这些类型，逗号分隔，如 01,06')
    ap.add_argument('--engine', choices=['native', 'ladybug'], default='native')
    ap.add_argument('--step', type=float, default=None, help='场地网格步长 m')
    a = ap.parse_args(argv)

    t_all = time.time()
    print('配置：', C.status())

    if not a.skip_data and not a.only:
        for s in DATA_ORDER:
            args = []
            if s == 'extract_climate.py':
                args = ['--engine', a.engine]
            if s == 'run_solar_site.py' and a.step:
                args = ['--step', str(a.step)]
            run(s, args)

    todo = [k for k in PLOT_ORDER if k in a.only.split(',')] if a.only else PLOT_ORDER
    for k in todo:
        run(STAGES[k])

    print('\n完成，用时 %.1f s；图集目录：%s' % (time.time() - t_all, C.OUTROOT))


if __name__ == '__main__':
    main()
