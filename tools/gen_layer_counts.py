# -*- coding: utf-8 -*-
"""统计各业务图层 GeoJSON 的要素数量，生成前端可用的数量清单。

输出：
1. frontend/src/api/layerCounts.generated.ts —— 构建期内嵌到 JS 包，
   图层面板直接 import，运行时不发请求（对 5173 / 8080 / VPS 部署一律生效）。
2. frontend/public/data/layers/counts.json + data/processed/geojson/counts.json
   —— 供人工核对 / 外部脚本使用。

数据更新（重新入库/解析 SHP）后重跑本脚本并重新构建前端即可刷新。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "frontend" / "public" / "data" / "layers"
DEPLOY_DIR = ROOT / "data" / "processed" / "geojson"
TS_OUT = ROOT / "frontend" / "src" / "api" / "layerCounts.generated.ts"

HEADER = """/**
 * 图层要素数量表（由 tools/gen_layer_counts.py 自动生成，勿手改）。
 * 数据更新后重跑脚本并重新构建前端即可刷新。
 */
export const LAYER_COUNTS: Record<string, number> = {
"""


def main() -> None:
    counts = {}
    for f in sorted(SRC_DIR.glob("*.geojson")):
        data = json.loads(f.read_text(encoding="utf-8"))
        n = len(data.get("features", [])) if isinstance(data, dict) else 0
        counts[f.stem] = n
        print(f"{f.stem:28s} {n}")

    body = "".join(f"  '{k}': {v},\n" for k, v in counts.items())
    TS_OUT.write_text(HEADER + body + "}\n", encoding="utf-8")
    print(f"\nwrote {TS_OUT}")

    out = json.dumps(counts, ensure_ascii=False, indent=2)
    (SRC_DIR / "counts.json").write_text(out + "\n", encoding="utf-8")
    print(f"wrote {SRC_DIR / 'counts.json'}")

    if DEPLOY_DIR.is_dir():
        (DEPLOY_DIR / "counts.json").write_text(out + "\n", encoding="utf-8")
        print(f"wrote {DEPLOY_DIR / 'counts.json'}")


if __name__ == "__main__":
    main()
