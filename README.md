# Architecture Design Three

同济《建筑设计 III · 空间进化》课程相关工作区。

---

## 目录

| 路径 | 内容 |
|---|---|
| [`skills/climate-atlas/`](skills/climate-atlas/) | 气候分析图集生成器：一份 `.epw` + 一个建筑模型 → 一整套气候分析图 |

---

## skills/climate-atlas · 气候分析图集生成器

把 Ladybug「Climate Analysis」那张一图出全集**拆成六类图式**，逐类重画。
只依赖 `numpy + matplotlib`，不需要 Ladybug Tools（需要与 LBT 生态逐位对齐时可切 `--engine ladybug`）。

### 三步跑起来

```bash
cd skills/climate-atlas
pip install -r requirements.txt
cp atlas.example.json atlas.json     # 改 epw / mesh / orientation / site
python scripts/atlas_config.py       # 自检：路径与真北向量
python scripts/run_all.py            # 出全套图，约 1 分钟
```

产物落在 `图集/`，按类型分子目录。只要某几类：

```bash
python scripts/run_all.py --skip-data --only 01,06
```

### 六类图式

| 类型 | 内容 | 需要几何 |
|---|---|---|
| 00 | 总图版（一页交付） | ✓ |
| 01 | 极坐标玫瑰：全年/逐月/四季风玫瑰、主导风向罗盘、太阳辐射玫瑰 | — |
| 02 | 太阳轨迹：12 条日弧、观测点遮挡轮廓、天穹着色 | ✓ |
| 03 | 逐时热图：6 参数 × 365 日 × 24 时 | — |
| 04 | 月度图表：温度/辐射/降水/舒适度占比 | — |
| 05 | 三维频次曲面：温度×钟点、温度×风速 | — |
| 06 | 建筑专题：场地日照率、阴影范围矩阵、立面得热潜力 | ✓ |

没有建筑模型也能出 9 张图（01/03/04/05）。

### 精度

原生引擎（NOAA 简化算法）与 Ladybug 实测对照（上海 CSWD 583620，8,760 h）：
太阳高度角 \|Δ\| max 0.91°、方位角 max 1.10°；「太阳在地平线上」小时 4,205 vs 4,221（−0.4%）；
风/温/辐射统计逐位一致（静风 3.56% = 312 h）。

### 文档

- [`SKILL.md`](skills/climate-atlas/SKILL.md) — 给 AI agent 的技能说明
- [`README.md`](skills/climate-atlas/README.md) — 完整说明（结构、配置、局限）
- [`references/figure-types.md`](skills/climate-atlas/references/figure-types.md) — 六类图式判读
- [`references/orientation.md`](skills/climate-atlas/references/orientation.md) — 模型朝向反解四条证据法
- [`references/metrics.md`](skills/climate-atlas/references/metrics.md) — 指标口径
- [`references/pitfalls.md`](skills/climate-atlas/references/pitfalls.md) — 12 个坑与排错顺序

---

## License

MIT
