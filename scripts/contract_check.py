"""
前后端契约校验：核对后端返回结构是否满足前端的 TypeScript 类型声明。

背景：前端 `src/types/*.ts` 声明了它消费的字段。切换到真实后端
（`VITE_USE_MOCK=false`）后，若后端字段缺失或改名，页面会在运行时静默出错。
本脚本把这件事变成可断言的检查。

用法：
    uvicorn main:app --port 8000      # 后端
    vite --host 127.0.0.1             # 前端（提供 /api 代理）
    <venv>/Scripts/python.exe scripts/contract_check.py [base_url]

默认走前端地址（顺带验证 Vite 代理链路）。
"""
from __future__ import annotations

import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5173"

AOI = {
    "type": "Polygon",
    "coordinates": [[[110.0, 25.0], [110.42, 25.0], [110.42, 25.5], [110.0, 25.5], [110.0, 25.0]]],
}

passed = failed = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}  {extra}")


def has_keys(obj: dict, keys: list[str]) -> tuple[bool, str]:
    missing = [k for k in keys if k not in obj]
    return (not missing), f"缺字段 {missing}"


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=120.0)

    print(f"\n目标：{BASE}（经 Vite 代理 → 后端）\n")

    # ---------- ScenarioSummary[] ----------
    print("--- 契约 A：ScenarioSummary / ScenarioDetail ---")
    r = c.get("/api/scenarios")
    check("GET /api/scenarios 可用（代理链路）", r.status_code == 200, str(r.status_code))
    items = r.json().get("items", [])
    ok, msg = has_keys(items[0], ["id", "name", "category", "description"])
    check("ScenarioSummary 字段齐全", ok, msg)
    check("门类数 = 10", len(items) == 10, str(len(items)))

    r = c.get("/api/scenarios/G")
    d = r.json()
    ok, msg = has_keys(d, ["id", "name", "category", "description",
                           "constraints", "factors", "weights_ahp"])
    check("ScenarioDetail 字段齐全", ok, msg)
    ok, msg = has_keys(d["constraints"][0], ["id", "name", "buffer_m", "required"])
    check("Constraint 字段齐全", ok, msg)
    ok, msg = has_keys(d["factors"][0], ["id", "name", "direction", "unit"])
    check("Factor 字段齐全", ok, msg)
    check("factors 为 5 维", len(d["factors"]) == 5, str(len(d["factors"])))
    check("direction 取值合法（1/-1/2）",
          all(f["direction"] in (1, -1, 2) for f in d["factors"]))
    check("weights_ahp 覆盖全部因子",
          set(d["weights_ahp"]) == {f["id"] for f in d["factors"]})
    check("weights_ahp 归一化", abs(sum(d["weights_ahp"].values()) - 1) < 0.01)

    # ---------- SelectionRequest / SelectionResponse ----------
    print("\n--- 契约 B：SelectionRequest → SelectionResponse ---")
    body = {
        "scenario_id": "G", "aoi": AOI, "grid_size_m": 30, "min_area_ha": 1.0,
        "top_n": 5, "alpha": 0.5, "algorithm": "topsis", "weights_override": None,
    }
    r = c.post("/api/selection/run", json=body)
    check("POST /api/selection/run 可用（代理链路）", r.status_code == 200, str(r.status_code)[:100])
    res = r.json()
    ok, msg = has_keys(res, ["task_id", "scenario_id", "grid_size_m",
                             "total_cells", "available_cells", "candidates", "message"])
    check("SelectionResponse 字段齐全", ok, msg)

    cand = res["candidates"][0]
    ok, msg = has_keys(cand, ["rank", "score", "area_ha", "geometry", "factors", "notes"])
    check("CandidateParcel 必需字段齐全", ok, msg)
    for opt in ("cluster", "code", "source"):
        check(f"CandidateParcel 可选字段 {opt} 存在（前端会读）", opt in cand)
    check("geometry 为 Polygon 形状可用",
          cand["geometry"].get("type") in ("Polygon", "MultiPolygon")
          and isinstance(cand["geometry"].get("coordinates"), list))
    check("factors 键与模板一致",
          set(cand["factors"]) == {f["id"] for f in d["factors"]},
          str(set(cand["factors"])))
    check("rank 从 1 连续编号",
          [x["rank"] for x in res["candidates"]] == list(range(1, len(res["candidates"]) + 1)))
    check("score 在 0–100", all(0 <= x["score"] <= 100 for x in res["candidates"]))
    check("area_ha 为正", all(x["area_ha"] > 0 for x in res["candidates"]))
    check("前端扩展字段 weights 已返回", "weights" in res and len(res["weights"]) == 5)
    check("前端扩展字段 sensitivity 已返回", "sensitivity" in res)

    # ---------- ParseResult ----------
    print("\n--- 契约 C：ParseResult（AI 需求解析）---")
    r = c.post("/api/ai/parse", json={"text": "为物流园区选址，占地面积约 500 亩"})
    p = r.json()
    ok, msg = has_keys(p, ["scenarioId", "scenarioName", "matchedKeywords",
                           "constraints", "weights", "explanation",
                           "targetAreaHa", "targetAreaText"])
    check("ParseResult 字段齐全", ok, msg)
    check("constraints 为字符串数组", isinstance(p["constraints"], list)
          and all(isinstance(x, str) for x in p["constraints"]))
    check("weights 为对象", isinstance(p["weights"], dict))

    # ---------- /api/ai/chat 返回纯字符串 ----------
    r = c.post("/api/ai/chat", json={"history": [], "text": "权重怎么设置"})
    check("POST /api/ai/chat 返回字符串", r.status_code == 200 and r.json().__class__ is str)

    # ---------- 图层静态资源（前端直连 public，不经后端）----------
    print("\n--- 契约 D：图层静态资源 ---")
    for lid in ("regulated-industrial", "eco-redline", "perm-farmland"):
        r = c.get(f"/data/layers/{lid}.geojson")
        ok = r.status_code == 200 and r.json().get("type") == "FeatureCollection"
        check(f"/data/layers/{lid}.geojson 可用", ok, str(r.status_code))

    print(f"\n{'=' * 56}\n通过 {passed} 项，失败 {failed} 项\n{'=' * 56}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
