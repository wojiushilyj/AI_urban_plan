"""
数据预处理：统一坐标系 → 生成派生因子 → 入库登记。

计划用法：
    python scripts/preprocess.py --input data/raw/xxx.shp --layer-id prime_farmland \
        --kind constraint --source "一张图成果" --sample 0

TODO(09-08)：实现
  1. gpd.read_file 读取，若 crs 为空则报错并退出（严禁"坐标系不明就入库"）
  2. to_crs(EPSG:4490) 统一存储坐标系
  3. 面积/长度量算前先切到 EPSG:4545
  4. 写入 data/processed/{layer_id}.geojson
  5. 在 SQLite 的 layer 表登记元信息（含 is_sample）
"""
import argparse


def main():
    ap = argparse.ArgumentParser(description="空间数据预处理与入库登记")
    ap.add_argument("--input", required=True, help="原始数据路径")
    ap.add_argument("--layer-id", required=True, help="图层 ID，见 docs/SCENARIOS.md")
    ap.add_argument("--kind", required=True, choices=["constraint", "factor", "base"])
    ap.add_argument("--source", default="", help="数据来源")
    ap.add_argument("--sample", type=int, default=1, help="1=样例数据（演示/申报须标注）")
    args = ap.parse_args()

    raise NotImplementedError("预处理脚本计划 09-08 交付，见 docs/PROGRESS.md")


if __name__ == "__main__":
    main()
