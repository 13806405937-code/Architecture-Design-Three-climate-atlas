# -*- coding: utf-8 -*-
"""climate_engine —— 朝向换算 / 建筑高度场 / 含遮挡的日照判定

设计要点
  1. 高度场法而不是逐面求交：三角面光栅化成 XY 高度场，某个 (x,y) 只要取最高 Z，
     就能回答"这条视线在离地 t 米处有没有被挡"，比逐三角形求交快 2–3 个数量级。
  2. 只判"地表 / 某一标高"的点：高度场丢掉了垂直面信息，所以不能做逐层窗视点遮挡。
  3. 朝向来自 atlas_config（唯一口径）：真北 = (-sinφ, cosφ)，φ = BRG_Y。
"""
import json
import math
import os

import numpy as np

import atlas_config as C

BASE = C.BASE
DATA = C.DATA
SITE = C.SITE

BRG_X = C.BRG_X           # 模型 +X 轴对应的真实方位角（自北顺时针，度）
BRG_Y = C.BRG_Y           # 模型 +Y 轴

_AX = math.radians(BRG_X)
_AY = math.radians(BRG_Y)
_VX = np.array([math.sin(_AX), math.cos(_AX)])     # +X 轴在真实 (E,N) 上的单位向量
_VY = np.array([math.sin(_AY), math.cos(_AY)])     # +Y 轴


def en_to_model(e, n):
    """真实 (East, North) 分量 -> 模型 (X, Y) 分量"""
    return e * _VX[0] + n * _VX[1], e * _VY[0] + n * _VY[1]


def true_north_in_model():
    """真北单位向量在模型 XY 平面上的表示"""
    return C.true_north_in_model()


def sun_dirs(alt_deg, azi_deg):
    """太阳高度角/方位角(deg) -> 模型坐标系下的单位向量 (N, 3)"""
    h = np.radians(np.asarray(alt_deg, dtype=float))
    a = np.radians(np.asarray(azi_deg, dtype=float))
    e = np.sin(a) * np.cos(h)
    n = np.cos(a) * np.cos(h)
    u = np.sin(h)
    sx = e * _VX[0] + n * _VX[1]
    sy = e * _VY[0] + n * _VY[1]
    return np.stack([sx, sy, u], axis=-1)


# ------------------------------------------------------------------ 数据载入
def _load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_climate():
    return _load_json(os.path.join(DATA, 'climate_data.json'))


def load_building(exclude_ground=True, min_vol=20.0):
    """载入建筑三角面。默认剔除场地底板与原点碎件。

    exclude_ground: 剔除 XY 覆盖近整个场地的薄板（地形板 / 底板）
    min_vol: 包围盒体积小于该值的对象视为碎件
    """
    d = _load_json(C.MESH_PATH)
    sx = SITE['xmax'] - SITE['xmin']
    sy = SITE['ymax'] - SITE['ymin']
    objs = []
    for o in d['objects']:
        b = o['bb']
        dx, dy, dz = b[3] - b[0], b[4] - b[1], b[5] - b[2]
        if exclude_ground and dx > 0.95 * sx and dy > 0.95 * sy and dz < 0.15 * sx:
            o['_is_ground'] = True
            continue
        if dx * dy * dz < min_vol:
            o['_is_ground'] = False
            continue
        o['_is_ground'] = False
        objs.append(o)
    if not objs:
        raise SystemExit('没有可用建筑对象：检查 %s 或调低 min_vol' % C.MESH_PATH)
    return objs


def all_triangles(objs):
    tris = []
    owner = []
    for k, o in enumerate(objs):
        v = np.array(o['verts'], dtype=float)
        for f in o['faces']:
            tris.append(v[f])
            owner.append(k)
    return np.array(tris), np.array(owner)


# ------------------------------------------------------------------ 高度场
def build_heightfield(tris, cell=None, zmax=40.0, xmin=None, ymin=None,
                      xmax=None, ymax=None):
    """三角面 -> XY 高度场（每格取最高 Z）。用于快速遮挡判定。"""
    cell = cell or float(SITE.get('cell', 1.0))
    xmin = SITE['xmin'] if xmin is None else xmin
    ymin = SITE['ymin'] if ymin is None else ymin
    xmax = SITE['xmax'] if xmax is None else xmax
    ymax = SITE['ymax'] if ymax is None else ymax

    nx = int(math.ceil((xmax - xmin) / cell)) + 1
    ny = int(math.ceil((ymax - ymin) / cell)) + 1
    hf = np.zeros((ny, nx), dtype=np.float32)

    for t in tris:
        xs, ys = t[:, 0], t[:, 1]
        nrm = np.cross(t[1] - t[0], t[2] - t[0])
        if abs(nrm[2]) < 1e-9:
            continue                                    # 垂直面不贡献高度
        i0 = max(0, int(math.floor((xs.min() - xmin) / cell)))
        i1 = min(nx - 1, int(math.ceil((xs.max() - xmin) / cell)))
        j0 = max(0, int(math.floor((ys.min() - ymin) / cell)))
        j1 = min(ny - 1, int(math.ceil((ys.max() - ymin) / cell)))
        if i1 < i0 or j1 < j0:
            continue
        gx, gy = np.meshgrid(xmin + (np.arange(i0, i1 + 1) + 0.5) * cell,
                             ymin + (np.arange(j0, j1 + 1) + 0.5) * cell)
        ax, ay = t[0, 0], t[0, 1]
        bx, by = t[1, 0], t[1, 1]
        cx, cy = t[2, 0], t[2, 1]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        l3 = 1.0 - l1 - l2
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not inside.any():
            continue
        z = t[0, 2] - (nrm[0] * (gx - ax) + nrm[1] * (gy - ay)) / nrm[2]
        z = np.where(inside, z, 0.0).astype(np.float32)
        np.maximum(hf[j0:j1 + 1, i0:i1 + 1], z, out=hf[j0:j1 + 1, i0:i1 + 1])

    hf[hf < 0] = 0.0
    return hf, cell


# ------------------------------------------------------------------ 遮挡
def sunlit(px, py, pz, dirs, hf, cell=1.0, step=2.0, zmax=30.0, max_t=320.0,
           xmin=0.0, ymin=0.0):
    """判定点是否受太阳照射（未被建筑高度场遮挡）

    px/py/pz : (N,) 测点
    dirs     : (M,3) 模型坐标系单位太阳向量（仅 alt>0 的时段）
    返回     : (N,M) bool
    """
    ny, nx = hf.shape
    px = np.asarray(px, dtype=np.float32)
    py = np.asarray(py, dtype=np.float32)
    pz = np.asarray(pz, dtype=np.float32)
    N = px.size
    M = dirs.shape[0]
    out = np.zeros((N, M), dtype=bool)
    zmin_dir = C.SUNUP_ZMIN

    for m in range(M):
        sx, sy, sz = float(dirs[m, 0]), float(dirs[m, 1]), float(dirs[m, 2])
        if sz <= zmin_dir:
            continue
        cap = min(max_t, (zmax - pz.min()) / sz)
        T = int(math.ceil(cap / step))
        if T <= 0:
            out[:, m] = True
            continue
        ts = (np.arange(1, T + 1, dtype=np.float32)) * step
        X = px[:, None] + sx * ts[None, :]
        Y = py[:, None] + sy * ts[None, :]
        Z = pz[:, None] + sz * ts[None, :]
        icol = np.rint((X - xmin) / cell).astype(np.int32)
        jrow = np.rint((Y - ymin) / cell).astype(np.int32)
        valid = (icol >= 0) & (icol < nx) & (jrow >= 0) & (jrow < ny)
        np.clip(icol, 0, nx - 1, out=icol)
        np.clip(jrow, 0, ny - 1, out=jrow)
        hgt = hf[jrow, icol]
        blocked = valid & (Z < hgt)
        out[:, m] = ~blocked.any(axis=1)
    return out


def sun_up(dirs):
    """太阳在地平线上的小时掩膜（与 sunlit 同一阈值）"""
    return dirs[:, 2] > C.SUNUP_ZMIN


# ------------------------------------------------------------------ 自测
if __name__ == '__main__':
    import time

    print(json.dumps(C.status(), ensure_ascii=False, indent=2))
    objs = load_building()
    tris, owner = all_triangles(objs)
    nvec = true_north_in_model()
    print('objects=%d triangles=%d' % (len(objs), len(tris)))
    print('true north in model XY = (%.3f, %.3f)' % (nvec[0], nvec[1]))

    t0 = time.time()
    hf, cell = build_heightfield(tris)
    print('heightfield %s in %.2f s  max=%.2f m' % (hf.shape, time.time() - t0, hf.max()))

    cd = load_climate()
    alt = np.array(cd['sunpath']['altitude_hourly'], dtype=float)
    azi = np.array(cd['sunpath']['azimuth_hourly'], dtype=float)
    dirs = sun_dirs(alt, azi)
    print('sun-up hours = %d' % sun_up(dirs).sum())
