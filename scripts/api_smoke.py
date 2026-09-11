"""
后端接口冒烟测试（HTTP 层，需先启动服务）。

用法：
    uvicorn main:app --port 8000          # 另开一个终端
    <venv>/Scripts/python.exe scripts/api_smoke.py [base_url]

覆盖：健康检查 / 场景模板 / 图层 / AI 解析 / 选址主流程（三种算法）/ 错误码。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

AOI = {
    "type": "Polygon",
    "coordinates": [[[110.0, 25.0], [110.42, 25.0], [110.42, 25.5], [110.0, 25.5], [110.0, 25.0]]],
}

passed = failed = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}" + (f"  {extra}" if extra else ""))
    else:
        failed += 1
        print(f"  [FAIL] {name}  {extra}")


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0)

    print("\n--- 健康检查 ---")
    r = c.get("/health")
    h = r.json()
    check("GET /health 200", r.status_code == 200)
    check("GeoPackage 就绪", h.get("gpkg_exists") is True, f"layers={h.get('layers')}")
    check("量算坐标系 = EPSG:4525", h["crs"]["measure"] == "EPSG:4525")

    print("\n--- 行业门类模板 ---")
    r = c.get("/api/scenarios")
    items = r.json()["items"]
    check("GET /api/scenarios 200", r.status_code == 200)
    check("门类数 = 10", len(items) == 10, f"实际 {len(items)}")
    r = c.get("/api/scenarios/G")
    d = r.json()
    check("GET /api/scenarios/G 200", r.status_code == 200)
    check("含 constraints/factors/weights_ahp",
          all(k in d for k in ("constraints", "factors", "weights_ahp")))
    check("门类不存在返回 404", c.get("/api/scenarios/ZZZ").status_code == 404)

    print("\n--- 空间图层 ---")
    r = c.get("/api/layers")
    lay = r.json()
    check("GET /api/layers 200", r.status_code == 200)
    # 图层数跟随 data/processed/layers_manifest.json，避免每加一个图层就假失败
    manifest_path = Path(__file__).resolve().parents[1] / "data" / "processed" / "layers_manifest.json"
    if manifest_path.exists():
        expect = len(json.loads(manifest_path.read_text(encoding="utf-8"))["layers"])
        check(f"图层数与清单一致（{expect}）", len(lay["layers"]) == expect,
              f"实际 {len(lay['layers'])}")
    check("图层数 > 0", len(lay["layers"]) > 0)
    check("全部图层可用", all(x.get("available") for x in lay["layers"]))
    check("分组非空", len(lay["groups"]) >= 5)
    r = c.get("/api/layers/eco-redline")
    fc = r.json()
    check("GET /api/layers/eco-redline 200", r.status_code == 200)
    check("返回 FeatureCollection", fc.get("type") == "FeatureCollection")
    check("内部字段已剔除",
          not any("Shape_Area" in (f.get("properties") or {}) for f in fc["features"]))
    check("图层不存在返回 404", c.get("/api/layers/nope").status_code == 404)

    print("\n--- AI 需求解析 ---")
    r = c.post("/api/ai/parse", json={"text": "为物流园区选址，占地面积约 500 亩，紧邻高速出入口"})
    p = r.json()
    check("POST /api/ai/parse 200", r.status_code == 200)
    check("识别门类 G", p["scenarioId"] == "G", p["scenarioName"])
    check("面积换算 500亩 ≈ 33.33 公顷", abs((p.get("targetAreaHa") or 0) - 33.33) < 0.02,
          str(p.get("targetAreaHa")))
    r = c.post("/api/ai/parse", json={"text": "为污水处理厂选址"})
    check("识别门类 N", r.json()["scenarioId"] == "N")
    r = c.post("/api/ai/parse", json={"text": "随便选址"})
    check("未命中时回落默认门类", r.json()["scenarioId"] == "B")
    r = c.post("/api/ai/chat", json={"history": [], "text": "权重怎么设置"})
    check("POST /api/ai/chat 200", r.status_code == 200 and len(r.text) > 10)

    print("\n--- 选址主流程 ---")
    for algo in ("topsis", "regression", "kmeans"):
        body = {
            "scenario_id": "G", "aoi": AOI, "grid_size_m": 30, "min_area_ha": 1.0,
            "top_n": 5, "alpha": 0.5, "algorithm": algo,
        }
        r = c.post("/api/selection/run", json=body)
        check(f"[{algo}] 200", r.status_code == 200, r.text[:120] if r.status_code != 200 else "")
        if r.status_code != 200:
            continue
        d = r.json()
        check(f"[{algo}] 候选池 145 图斑", d["total_cells"] == 145, str(d["total_cells"]))
        check(f"[{algo}] 有可行地块", d["available_cells"] > 0, str(d["available_cells"]))
        check(f"[{algo}] 输出 Top-5", len(d["candidates"]) == 5)
        check(f"[{algo}] 几何为 4490 Polygon",
              all(x["geometry"]["type"] in ("Polygon", "MultiPolygon") for x in d["candidates"]))
        check(f"[{algo}] 五维因子齐全",
              all(set(x["factors"]) == {"urban_planning", "transport", "industry",
                                        "infrastructure", "cost"} for x in d["candidates"]))
        check(f"[{algo}] 权重归一化", abs(sum(d["weights"].values()) - 1.0) < 0.01,
              str(round(sum(d["weights"].values()), 4)))
        check(f"[{algo}] 得分有区分度",
              len({x["score"] for x in d["candidates"]}) > 1)
        if algo == "kmeans":
            check("[kmeans] 返回聚类分组", all(x.get("cluster") is not None for x in d["candidates"]))
        if algo == "topsis":
            task_id = d["task_id"]
            check("[topsis] message 如实说明缺数据约束", "未参与计算" in d["message"] or "已参与计算" in d["message"])

    print("\n--- 面积约束 ---")
    r = c.post("/api/selection/run", json={
        "scenario_id": "G", "aoi": AOI, "min_area_ha": 1.0, "top_n": 3, "target_area_ha": 8, "area_tolerance": 0.5})
    d = r.json()
    check("目标 8 公顷 ±50% → 可行数下降", d["available_cells"] < 107, str(d["available_cells"]))
    check("候选面积落在 4–12 公顷",
          all(4.0 <= x["area_ha"] <= 12.0 for x in d["candidates"]),
          str([x["area_ha"] for x in d["candidates"]]))
    check("说明含规模区间", "4.0–12.0" in d["message"], d["message"][:120])

    print("\n--- 结果落库 ---")
    r = c.get(f"/api/selection/result/{task_id}")
    check("GET /api/selection/result/{id} 200", r.status_code == 200)
    check("可读回排名", r.json()["result"]["candidates"][0]["rank"] == 1)
    check("任务不存在返回 404", c.get("/api/selection/result/nope").status_code == 404)

    print("\n--- 静态图层挂载 ---")
    r = c.get("/data/layers/eco-redline.geojson")
    check("GET /data/layers/*.geojson 200", r.status_code == 200)

    # ------------------------------------------------------------------ #
    # AI 能力：偏好学习模型 + 可解释性 + 稳健性
    # ------------------------------------------------------------------ #
    print("\n--- AI 偏好学习模型 ---")
    r = c.get("/api/ai/model")
    check("GET /api/ai/model 200", r.status_code == 200)
    m = r.json()
    check("模型可用", m.get("available") is True, str(m.get("reason"))[:80])
    if m.get("available"):
        check("样本量与实测一致", m["samples"] == 145 and m["positives"] == 66,
              f"{m.get('samples')}/{m.get('positives')}")
        check("报告交叉验证 AUC", 0.5 < m["metrics"]["auc_mean"] < 1.0,
              str(m["metrics"]["auc_mean"]))
        check("AUC 高于随机基线 0.5", m["metrics"]["auc_mean"] > 0.5)
        check("学习权重和为 1", abs(sum(m["learned_weights"].values()) - 1) < 0.01)
        check("学习权重覆盖 5 个维度", len(m["learned_weights"]) == 5)
        check("含消融实验", len(m.get("ablation", {})) >= 3)
        check("含单特征 AUC", len(m.get("univariate_auc", {})) >= 4)
        check("声明数据泄漏规避策略", "leakage_note" in m and len(m["leakage_note"]) > 20)
        # 泄漏审计的关键结论必须可复核：特征里不能出现 cost（含建筑密度）
        check("特征不含 cost（规避泄漏）", "cost" not in m["features"], str(m["features"]))
        check("负系数维度不给正权重",
              all(m["learned_weights"][f] == 0 or m["coefficients"][f] >= 0
                  for f in m["features"] if f in m["learned_weights"]))

    r = c.get("/api/ai/model/parcels?limit=10")
    check("GET /api/ai/model/parcels 200", r.status_code == 200)
    pj = r.json()
    check("样本明细非空", len(pj.get("items", [])) == 10)
    check("样本含真实标签", all(x["label"] in (0, 1) for x in pj["items"]))

    print("\n--- 权重来源切换（AI 接入点）---")
    base_body = {"scenario_id": "G", "aoi": AOI, "top_n": 3, "algorithm": "topsis"}
    wmap = {}
    for mode in ("expert", "learned", "blended"):
        r = c.post("/api/selection/run", json={**base_body, "weight_mode": mode})
        check(f"[{mode}] 200", r.status_code == 200)
        d = r.json()
        wmap[mode] = d["weights"]
        check(f"[{mode}] 声明了权重来源", len(d["weight_source"]) > 4, d["weight_source"])
        check(f"[{mode}] 权重和为 1", abs(sum(d["weights"].values()) - 1) < 0.01)
        check(f"[{mode}] 回传专家权重作对照", set(d["expert_weights"]) == set(d["weights"]))
    check("learned 与 expert 权重不同", wmap["learned"] != wmap["expert"],
          f"learned={wmap['learned']} expert={wmap['expert']}")

    print("\n--- 可解释 AI：因子贡献分解 ---")
    r = c.post("/api/selection/run", json=base_body)
    d = r.json()
    c0 = d["candidates"][0]
    check("候选含 contributions", len(c0["contributions"]) == 5, str(c0.get("contributions")))
    check("贡献有正有负（优势/短板可区分）",
          any(v > 0 for v in c0["contributions"].values())
          and any(v < 0 for v in c0["contributions"].values()))
    check("top_driver 是正贡献项",
          c0["top_driver"] and c0["contributions"][c0["top_driver"]] > 0)
    check("top_weakness 是负贡献项",
          c0["top_weakness"] and c0["contributions"][c0["top_weakness"]] < 0)
    check("sensitivity 为平均绝对贡献（非负）",
          all(v >= 0 for v in d["sensitivity"].values()), str(d["sensitivity"]))
    check("候选含 build_density（拆迁量）",
          all(0.0 <= x["build_density"] <= 1.0 for x in d["candidates"]))

    print("\n--- 稳健性：蒙特卡洛入选概率 ---")
    check("返回 robustness", isinstance(d["robustness"], dict) and d["robustness"])
    rb = d["robustness"]
    check("扰动 200 次", rb.get("samples") == 200, str(rb.get("samples")))
    check("每个 Top-N 都有入选概率", len(rb.get("prob_top_n", [])) == len(d["candidates"]))
    check("概率在 0–1 之间",
          all(0.0 <= p <= 1.0 for p in rb.get("prob_top_n", [])), str(rb.get("prob_top_n")))
    check("候选地块带 robustness 字段",
          all(x.get("robustness") is not None for x in d["candidates"]))
    check("排名越靠前概率越高",
          rb["prob_top_n"] == sorted(rb["prob_top_n"], reverse=True), str(rb["prob_top_n"]))

    print(f"\n{'=' * 56}\n通过 {passed} 项，失败 {failed} 项\n{'=' * 56}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
