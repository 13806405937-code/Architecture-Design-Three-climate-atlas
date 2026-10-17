# -*- coding: utf-8 -*-
"""atlas_config —— 全局配置解析（路径 + 模型朝向）

所有脚本只从这里取 BASE / DATA / OUTROOT / BRG_X / BRG_Y，不允许再写字面量路径。

配置文件查找顺序（先命中先用）：
  1. 环境变量 ATLAS_CONFIG 指向的 json
  2. 当前工作目录的 atlas.json
  3. 技能根目录的 atlas.json
  4. 技能根目录的 atlas.example.json（占位值，BASE 取当前目录）
  5. 全都没有 → 用内置默认值（BASE = 技能根目录）

朝向约定（★ 全包唯一口径）
  真北在模型 XY 平面内 = (-sin φ, cos φ)，其中 φ = BRG_Y。
  等价说法：模型 +Y 轴的方位角 = BRG_Y，模型 +X 轴的方位角 = BRG_X = BRG_Y + 90。
  方位角一律「自北顺时针，0–360」；模型 XY 一律「右手系，X 向右 Y 向上」。
"""
import json
import math
import os

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_DEFAULT = {
    "base": ".",
    "epw": "weather/site.epw",
    "mesh": "data/building_mesh.json",
    "out": "图集",
    "orientation": {"brg_x": 90.0},
    "site": {"xmin": 0.0, "ymin": 0.0, "xmax": 180.0, "ymax": 180.0, "cell": 1.0, "step": 2.0},
    "sunup_zmin": 0.04,
    "dpi": 200,
}


def _candidates():
    env = os.environ.get("ATLAS_CONFIG")
    if env:
        yield env
    yield os.path.join(os.getcwd(), "atlas.json")
    yield os.path.join(SKILL_ROOT, "atlas.json")
    yield os.path.join(SKILL_ROOT, "atlas.example.json")


def find_config():
    for p in _candidates():
        if p and os.path.isfile(p):
            return os.path.abspath(p)
    return None


def load():
    cfg = json.loads(json.dumps(_DEFAULT))          # deep copy
    path = find_config()
    if path:
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        if not isinstance(user, dict):
            raise SystemExit("atlas.json 顶层必须是对象")
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
        cfg["_config_path"] = path
    else:
        cfg["_config_path"] = None

    base = cfg.get("base") or "."
    if not os.path.isabs(base):
        anchor = os.path.dirname(path) if path else SKILL_ROOT
        base = os.path.abspath(os.path.join(anchor, base))
    cfg["base"] = base
    return cfg


CFG = load()

BASE = CFG["base"]
DATA = os.path.join(BASE, "data")
OUTROOT = os.path.join(BASE, CFG.get("out") or "图集")
EPW_PATH = CFG["epw"] if os.path.isabs(CFG["epw"]) else os.path.join(BASE, CFG["epw"])
MESH_PATH = CFG["mesh"] if os.path.isabs(CFG["mesh"]) else os.path.join(BASE, CFG["mesh"])
SITE = CFG["site"]
SUNUP_ZMIN = float(CFG.get("sunup_zmin", 0.04))
DPI = int(CFG.get("dpi", 200))

# ---- 朝向 ---------------------------------------------------------------
# orientation 允许三种写法（优先级从高到低）：
#   {"brg_y": 24.5}            ← 直接给 +Y 的方位角（推荐，最不容易错）
#   {"brg_x": 114.5}           ← 给 +X 的方位角
#   {"true_north_in_model":[x,y]}  ← 给真北在模型 XY 内的单位向量
#   {"world_axes": true}       ← 模型 +X 就是正东、+Y 就是正北
_ori = CFG.get("orientation") or {}
if _ori.get("world_axes"):
    BRG_Y = 0.0
    BRG_X = 90.0
elif "brg_y" in _ori:
    BRG_Y = float(_ori["brg_y"]) % 360.0
    BRG_X = (BRG_Y + 90.0) % 360.0
elif "brg_x" in _ori:
    BRG_X = float(_ori["brg_x"]) % 360.0
    BRG_Y = (BRG_X - 90.0) % 360.0
elif "true_north_in_model" in _ori:
    vx, vy = float(_ori["true_north_in_model"][0]), float(_ori["true_north_in_model"][1])
    n = math.hypot(vx, vy) or 1.0
    vx, vy = vx / n, vy / n
    # 真北 = (-sinφ, cosφ)  →  φ = atan2(-vx, vy)
    BRG_Y = math.degrees(math.atan2(-vx, vy)) % 360.0
    BRG_X = (BRG_Y + 90.0) % 360.0
else:
    BRG_X = float(_ori.get("brg_x", 90.0)) % 360.0
    BRG_Y = (BRG_X - 90.0) % 360.0


def status():
    return {
        "config": CFG.get("_config_path"),
        "base": BASE,
        "epw": EPW_PATH,
        "mesh": MESH_PATH,
        "out": OUTROOT,
        "brg_x": round(BRG_X, 2),
        "brg_y": round(BRG_Y, 2),
        "true_north_in_model": [round(true_north_in_model()[0], 4),
                                round(true_north_in_model()[1], 4)],
        "site": SITE,
    }


def true_north_in_model():
    """真北单位向量在模型 XY 平面内的表示"""
    r = math.radians(BRG_Y)
    return -math.sin(r), math.cos(r)


if __name__ == "__main__":
    print(json.dumps(status(), ensure_ascii=False, indent=2))
