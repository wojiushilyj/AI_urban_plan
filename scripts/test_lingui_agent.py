import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.agent.langgraph_agent import pharma_site_agent

init_state = {
    "user_query": "桂林临桂区建设现代生物医药研发总部与GMP生产基地，要求临近高校产学研平台并靠近快速干线，需开展集中连片与分地块方案比选",
    "project_profile": {
        "hq_min_ha": 1.0,
        "hq_max_ha": 8.0,
        "factory_min_ha": 5.0,
        "factory_max_ha": 25.0,
        "sanitary_buffer_m": 300.0,
    },
    "raw_candidates": {},
    "audited_candidates": {},
    "evaluated_candidates": {},
    "scheme_comparison": {},
    "opinion_report": "",
    "logs": [],
    "error": None,
}

res = pharma_site_agent.invoke(init_state)
evaluated = res["evaluated_candidates"]
print("=== LangGraph Run Success ===")
print("HQ candidates count:", len(evaluated.get("hq", [])))
for i, h in enumerate(evaluated.get("hq", [])[:5]):
    lon, lat = h["centroid_lon"], h["centroid_lat"]
    in_lingui = (109.90 <= lon <= 110.25 and 25.00 <= lat <= 25.40)
    print(f"  HQ #{i+1}: ID={h['id']} {h['land_type']} {h['area_ha']}ha, Total={h['scores']['total']}, Lon={lon:.4f}, Lat={lat:.4f}, InLingui={in_lingui}")

print("Factory candidates count:", len(evaluated.get("factory", [])))
for i, f in enumerate(evaluated.get("factory", [])[:5]):
    lon, lat = f["centroid_lon"], f["centroid_lat"]
    in_lingui = (109.90 <= lon <= 110.25 and 25.00 <= lat <= 25.40)
    print(f"  Factory #{i+1}: ID={f['id']} {f['land_type']} {f['area_ha']}ha, Total={f['scores']['total']}, Lon={lon:.4f}, Lat={lat:.4f}, InLingui={in_lingui}")

comp = res["scheme_comparison"]["dual_site_scheme"]
print(f"Commute Distance: {comp['commute_dist_km']} km, Car Time: {comp['commute_car_min']} min")
