---
name: climate-atlas
description: 用 EPW 气象文件 + 建筑模型批量生成一套"气候分析图集"（风玫瑰、太阳轨迹、逐时热图、月度图表、三维频次曲面、含遮挡的场地日照专题）。当用户要复刻 Ladybug Climate Analysis 的一图出全集、要按图式分类出图、要算含建筑遮挡的日照率/阴影范围、或者要反解导入模型（Rhino/SketchUp/FBX/OBJ）的真实朝向时使用。也用于给建筑前期分析、场地气候研究、绿色建筑报告成批配图。
agent_created: true
---

# Climate Atlas · 气候分析图集

把一套气候图从前提到成图固化下来：**读 EPW → 反解模型朝向 → 含遮挡日照引擎 → 按六类图式出图**。
不需要 Ladybug Tools，只需要 `numpy + matplotlib`；需要与 LBT 生态逐位对齐时切 `--engine ladybug`。

## 何时用这个技能

- 手上有一个 `.epw`（气象文件）和一份建筑模型，要出一整套气候分析图；
- 用户拿来一张 Ladybug「Climate Analysis」的合成图，说"照这个做一组"——本技能就是那张图的可复现拆解；
- 只要其中一类图（例如"含遮挡的场地日照率分布"或"阴影范围矩阵"）——单跑对应脚本即可；
- 模型是从 Rhino/SketchUp/FBX/OBJ 导入的，**不知道朝向**——先走 `references/orientation.md` 的四条证据法。

## 先读这三件（按顺序）

| 想知道 | 读 |
|---|---|
| 六类图式分别是什么、怎么判读 | `references/figure-types.md` |
| 模型朝向怎么反解、180° 歧义怎么破 | `references/orientation.md` |
| 指标口径（日照率、静风、云量、可照时数） | `references/metrics.md` |
| 踩过的坑（错一个整图就废） | `references/pitfalls.md` |

## 快速开始

```bash
cp atlas.example.json atlas.json     # 改 epw / mesh / orientation / site
python scripts/atlas_config.py       # 自检：打印解析出的路径与真北向量
python scripts/run_all.py            # 数据 + 全部 7 类图，约 1–2 分钟
```

只要某几类：

```bash
python scripts/run_all.py --skip-data --only 01,06
```

分步跑（排错时用这个顺序）：

```bash
python scripts/extract_climate.py    # → data/climate_data.json（统计量）
python scripts/extract_epw_raw.py    # → data/epw_hourly.json（逐时原值）
python scripts/run_solar_site.py     # → data/sunhours_grid.json（含遮挡日照，最慢，10–60 s）
python scripts/plot_01_polar.py      # 01 极坐标玫瑰族
python scripts/plot_03_04_series.py  # 03 逐时热图 + 04 月度图表
python scripts/plot_02_05_sun.py     # 02 太阳轨迹 + 05 三维曲面
python scripts/plot_06_building.py   # 06 建筑专题（需 mesh）
python scripts/plot_00_overview.py   # 00 总图版（需前几步的产物）
python scripts/plot_99_index.py      # 99 图集总览（必须最后）
```

产物全部落在 `atlas.json` 的 `out` 目录（默认 `图集/`），按类型分子目录。

## 配置：唯一入口是 atlas.json

查找顺序：`$ATLAS_CONFIG` → `./atlas.json` → 技能根 `atlas.json` → `atlas.example.json` → 内置默认值。
**任何脚本都不许写死路径**，一律 `import atlas_config as C` 取 `C.BASE / C.DATA / C.OUTROOT / C.BRG_X / C.BRG_Y / C.SITE`。

最小可跑配置：

```json
{
  "epw": "weather/site.epw",
  "mesh": "data/building_mesh.json",
  "orientation": { "brg_y": 24.5 },
  "site": { "xmin": 0, "ymin": 0, "xmax": 180, "ymax": 180, "cell": 1.0, "step": 2.0 }
}
```

## 朝向是唯一口径，必须显式给

全包只认一种表述：**真北在模型 XY 平面内 = (−sin φ, cos φ)，φ = `brg_y`**，
即模型 +Y 轴的方位角为 `brg_y`、+X 轴为 `brg_y + 90`（方位角自北顺时针 0–360，模型 XY 右手系）。

`orientation` 四种写法任选其一：`world_axes: true`（+Y 就是正北）｜`brg_y`｜`brg_x`｜`true_north_in_model:[x,y]`。
**不要跳过这一步直接出图**——朝向错 90°，风玫瑰与阴影全对不上，而图上看不出来。反解流程见 `references/orientation.md`。

## 建筑模型输入格式

`mesh` 指向一个 JSON：

```json
{ "units": "m",
  "objects": [ { "name": "block_01",
                 "verts": [[x,y,z], ...],
                 "faces": [[i,j,k], ...],
                 "bb": [xmin, ymin, zmin, xmax, ymax, zmax] } ] }
```

- 单位一律**米**；坐标用模型自身 XY，不需要预旋转（旋转由 `orientation` 负责）。
- `faces` 只支持三角面。从 Rhino/SU/FBX 导出后先三角化。
- 缺 `bb` 时会被算体积——宁可多给，别少给。
- 覆盖整个场地的薄板（地形板/底板）会被自动识别并剔除；判据是「XY 覆盖 >95% 场地且厚度 <15% 场宽」。

## 六类图式（产出对照）

| 类型 | 需要什么 | 脚本 | 典型张数 |
|---|---|---|---|
| 00 总图版 | 全部 | `plot_00_overview.py` | 1 |
| 01 极坐标玫瑰族 | 只有 EPW | `plot_01_polar.py` | 5 |
| 02 太阳轨迹族 | EPW + mesh | `plot_02_05_sun.py` | 3 |
| 03 逐时热图族 | EPW（逐时原值） | `plot_03_04_series.py` | 1 |
| 04 月度图表族 | EPW 统计 | `plot_03_04_series.py` | 1 |
| 05 三维频次曲面族 | EPW（逐时原值） | `plot_02_05_sun.py` | 2 |
| 06 建筑专题族 | EPW + mesh + 日照网格 | `plot_06_building.py` | 3 |

**没有建筑模型也能出 01/03/04/05**（共 9 张）。只有 02/06 与总图版需要几何。

## 核心算法（改代码前必读）

- **高度场遮挡**：三角面 → XY 高度场（每格取最高 Z，跳过垂直面）→ 沿太阳方向每 2 m 采样，任一步 `Z < h` 即判为阴影。目的是判地表/某一标高的点，**不做逐层窗视点遮挡**（高度场丢掉了垂直面信息）。
- **可照时数**：「太阳在地平线上」定义为太阳方向向量 Z 分量 > `sunup_zmin`（默认 0.04 ≈ 高度角 2.29°）。这个阈值同时决定 `sunlit` 与统计分母，**改一处两处都变**。
- **日照率** = 受照时数 ÷ 该时段可照时数。三张场地日照图必须用同一分母口径才能横向比较。
- **太阳位置**：`epw_native.solar_position`（NOAA 简化）。方位角必须 `atan2(e, n)`，**不能用 acos 分支反解**（会整体镜像 180°）。

## 已知局限（写进图注，别当成 bug）

1. 高度场法只判地表点，不能给立面逐窗日照；立面只出「朝向加权得热潜力」。
2. native 引擎与 ladybug 的太阳位置差 ≤1.1°；「太阳在地平线上」小时数 4,205 vs 4,221（差 0.4%）；场地日照时数逐点差 ≤23 h（均值 10.5 h / 4,221 h）。要逐位对齐就 `--engine ladybug`。
3. 云量按 EPW 总云量十分制处理；`climate_data.json` 的 `cloud_mean_pct` 已归一为百分比，与 ladybug 原始 okta 均值不是同一量纲。
4. 图上的项目名、署名全部来自 `labels`，**换项目忘了改就会印错标题**。

## 依赖

`numpy`、`matplotlib`（必需）；`Pillow`（仅 `plot_99_index.py` 拼总览用）；`ladybug`（仅 `--engine ladybug`）。
字体默认 `Microsoft YaHei → SimHei → Arial`，Linux/macOS 上改 `plot_common.py` 的 `rcParams` 或装中文字体。
