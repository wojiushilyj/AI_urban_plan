"""
选址引擎冒烟测试（不依赖 HTTP 服务，直接调用引擎）。

用法：
    cd AI_urban_plan
    <venv>/Scripts/python.exe scripts/engine_smoke.py
    <venv>/Scripts/python.exe scripts/engine_smoke.py G --area 33.3   # 指定门类与目标规模(公顷)

默认研究区 = 桂林市临桂区（与前端 store/map.ts 的 LINGUI_AOI 一致，EPSG:4490）。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas.selection import SelectionRequest          # noqa: E402
from app.services.suitability import run_selection          # noqa: E402
from app.services import spatial                            # noqa: E402

# 桂林市临桂区（简化外包矩形，EPSG:4490）—— 与前端默认 AOI 一致
LINGUI_AOI = {
    "type": "Polygon",
    "coordinates": [[[110.0, 25.0], [110.42, 25.0], [110.42, 25.5], [110.0, 25.5], [110.0, 25.0]]],
}

SCENARIOS = ["B", "C2", "G", "N"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", nargs="?", default=None, help="行业门类 id，缺省跑多个")
    ap.add_argument("--area", type=float, default=None, help="目标用地规模（公顷）")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--algo", default="topsis", choices=["topsis", "regression", "kmeans"])
    args = ap.parse_args()

    print("=" * 72)
    print("数据自检")
    print("=" * 72)
    ids = spatial.available_layer_ids()
    print(f"  GeoPackage : {spatial.GPKG_PATH}")
    print(f"  存在       : {spatial.GPKG_PATH.exists()}")
    print(f"  图层数     : {len(ids)}")
    if not spatial.GPKG_PATH.exists():
        print("  ✗ 数据文件缺失，请先运行 scripts/preprocess.py 生成 layers.gpkg")
        return 1
    for lid in ("regulated-industrial", "eco-redline", "perm-farmland", "road-network"):
        gdf = spatial.load_layer(lid)
        print(f"    {lid:24s} {len(gdf):5d} 要素  {gdf.crs}")
    print()

    targets = [args.scenario] if args.scenario else SCENARIOS
    for sid in targets:
        req = SelectionRequest(
            scenario_id=sid,
            aoi=LINGUI_AOI,
            grid_size_m=30,
            min_area_ha=1.0,
            top_n=args.top,
            alpha=0.5,
            algorithm=args.algo,
            target_area_ha=args.area,
        )
        t0 = time.perf_counter()
        res = run_selection(req)
        dt = (time.perf_counter() - t0) * 1000

        print("=" * 72)
        print(f"门类 {sid} ｜ 算法 {args.algo} ｜ 耗时 {dt:.0f} ms")
        print("=" * 72)
        print(f"  候选池 {res.total_cells} 个图斑 → 可行 {res.available_cells} 个 → 输出 {len(res.candidates)} 个")
        print(f"  有效权重: " + ", ".join(f"{k}={v}" for k, v in res.weights.items()))
        if res.sensitivity:
            print(f"  权重敏感性: {res.sensitivity}")
        print(f"  说明: {res.message}")
        print()
        for c in res.candidates:
            print(f"  #{c.rank} {c.code}  得分 {c.score:5.1f}  面积 {c.area_ha:8.2f} ha")
            print(f"       因子: " + "  ".join(f"{k}={v}" for k, v in c.factors.items()))
            print(f"       {c.notes}")
        if not res.candidates:
            print("  ✗ 无候选地块")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
