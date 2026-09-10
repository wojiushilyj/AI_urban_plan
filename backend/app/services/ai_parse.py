"""
AI 需求解析与对话（规则版，LLM 可选增强）。

设计原则（README 铁律）：**无 LLM Key 时必须可跑通全流程**。
因此解析主逻辑是确定性的关键词 + 正则，LLM 仅在配置开启时用于润色/兜底。

换算口径与前端 `frontend/src/utils/area.ts` 保持一致（1 公顷 = 15 亩 = 10000 m²）。
"""
from __future__ import annotations

import re
from typing import Any

from app.config import settings
from app.services.scenarios import SCENARIOS

# --------------------------------------------------------------------------- #
# 关键词 → 行业门类（顺序即优先级，具体词在前）
# --------------------------------------------------------------------------- #

KEYWORD_MAP: list[tuple[list[str], str]] = [
    (["矿", "采矿", "砂石", "石料", "矿权", "采石"], "B"),
    (["消费品", "食品", "纺织", "服装", "家具", "家电", "轻工", "日用"], "C1"),
    (["原材料", "钢铁", "化工", "建材", "造纸", "石化", "有色", "水泥", "中间品"], "C2"),
    (["装备", "机械", "汽车", "电子", "船舶", "航空航天", "设备", "制造"], "C3"),
    (["电力", "热力", "燃气", "供水", "电厂", "电站", "变电站", "能源", "水生产"], "D"),
    (["建筑", "施工", "搅拌站", "预制", "构件", "混凝土"], "E"),
    (["物流", "仓储", "货运", "快递", "邮政", "枢纽", "分拨", "交通运输"], "G"),
    (["信息", "软件", "数据", "互联网", "通信", "数据中心", "云计算"], "I"),
    (["科研", "科学", "研究", "实验室", "检验", "检测", "研发"], "M"),
    (["水利", "环保", "污水", "垃圾", "固废", "环卫", "公共设施", "环境"], "N"),
]

DEFAULT_SCENARIO_ID = "B"

# --------------------------------------------------------------------------- #
# 用地规模解析（1 公顷 = 15 亩 = 10000 m²）
# --------------------------------------------------------------------------- #

MU_PER_HA = 15
MIN_HA, MAX_HA = 0.05, 5000.0

_AREA_UNITS: list[tuple[str, float, str]] = [
    (r"万平方(?:米|公尺)|万平米|万㎡|万m²|万m2", 1.0, "万平方米"),
    (r"平方(?:公里|千米)|k㎡|km²|km2", 100.0, "平方公里"),
    (r"万亩", 10000.0 / MU_PER_HA, "万亩"),
    (r"公顷|平方百米|hectare|ha(?![a-z])", 1.0, "公顷"),
    (r"亩", 1.0 / MU_PER_HA, "亩"),
    (r"平方(?:米|公尺)|平米|㎡|m²|m2", 1.0 / 10000.0, "平方米"),
]

_AREA_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(" + "|".join(u[0] for u in _AREA_UNITS) + r")",
    re.IGNORECASE,
)


def parse_area_requirement(text: str) -> dict[str, Any] | None:
    """从需求文本抽取「数字 + 面积单位」→ 目标公顷数。未提及或超合理范围返回 None。"""
    m = _AREA_RE.search(text)
    if not m:
        return None
    value = float(m.group(1))
    token = m.group(2)
    for pattern, to_ha, label in _AREA_UNITS:
        if re.fullmatch(pattern, token, re.IGNORECASE):
            if value <= 0:
                return None
            target_ha = value * to_ha
            if target_ha < MIN_HA or target_ha > MAX_HA:
                return None
            return {
                "target_ha": round(target_ha, 2),
                "text": re.sub(r"\s+", "", m.group(0)),
                "unit": label,
                "value": value,
            }
    return None


# --------------------------------------------------------------------------- #
# 需求解析
# --------------------------------------------------------------------------- #

def parse_requirement(text: str) -> dict[str, Any]:
    """自然语言选址需求 → 行业门类 + 约束建议 + 权重 + 用地规模。"""
    text = text or ""
    matched = [kw for kws, _ in KEYWORD_MAP for kw in kws if kw in text]

    scenario_id = DEFAULT_SCENARIO_ID
    for kws, sid in KEYWORD_MAP:
        if any(kw in text for kw in kws):
            scenario_id = sid
            break

    scenario = SCENARIOS[scenario_id]
    weights = dict(scenario["weights_ahp"])
    total = sum(weights.values()) or 1.0
    weights = {k: round(v / total, 2) for k, v in weights.items()}

    # 硬约束全部建议启用（required 为不可关闭项，其余按门类默认建议）
    constraints = [c["id"] for c in scenario["constraints"]]

    area = parse_area_requirement(text)
    explanation = (
        f"已解析您的选址需求：识别到行业门类「{scenario['name']}」"
        + (f"（命中关键词：{'、'.join(matched)}）" if matched else "")
        + f"；建议启用 {len(constraints)} 项硬约束"
        + (f"，用地规模目标约 {area['target_ha']} 公顷（原表述「{area['text']}」）" if area else "")
        + "。权重可在「选址偏好」中调整。"
    )

    return {
        "scenarioId": scenario_id,
        "scenarioName": scenario["name"],
        "matchedKeywords": matched,
        "constraints": constraints,
        "weights": weights,
        "explanation": explanation,
        "targetAreaHa": area["target_ha"] if area else None,
        "targetAreaText": area["text"] if area else None,
    }


# --------------------------------------------------------------------------- #
# 对话（确定性 FAQ，LLM 开启时可接管）
# --------------------------------------------------------------------------- #

_FAQ: list[tuple[tuple[str, ...], str]] = [
    (("权重", "偏好"),
     "指标权重由「选址偏好」的三档（在意/一般/不在意）决定，对应基值 5/3/1，"
     "系统自动归一化为 5 个维度（城市规划/交通物流/产业协同/基础配套/建造成本）的权重，权重和恒为 1。"),
    (("约束", "红线", "农田"),
     "硬约束为布尔一票否决项：永久基本农田、生态保护红线命中即剔除。带缓冲距离的约束"
     "（如河湖管理范围 30m、高速保护距离 100m）会自动应用缓冲后判定。"
     "当前库中没有图层数据的约束会被如实跳过，并在结果说明中列明。"),
    (("占地", "面积", "规模"),
     "需求里提到占地面积时（如「约 500 亩」「20 公顷」「10 万平方米」），系统换算为公顷作为目标规模，"
     "并按 ±50% 浮动区间筛选候选地块。该浮动限值为初值，最终由算法设计人员按行业门类核定。"),
    (("算法", "TOPSIS", "聚类", "回归"),
     "支持三种算法：TOPSIS（逼近理想解排序，适合综合评价）、多元回归（线性加权拟合偏好）、"
     "K-Means 聚类（按因子特征自动分 3 组，聚类优先排序）。竞赛演示推荐 TOPSIS。"),
    (("导出", "报告"),
     "计算完成后可在右侧「报告导出」生成选址报告，支持 PDF（打印）、Excel（权重与候选表）、"
     "图纸图片三种格式。"),
]


def chat_reply(history: list[dict[str, Any]], text: str) -> str:
    """对话回复。命中 FAQ 则返回对应解释，否则返回能力说明。"""
    q = text or ""
    if not q and history:
        q = str(history[-1].get("content", ""))
    for keys, answer in _FAQ:
        if any(k in q for k in keys):
            return answer
    return (
        "收到您的需求。我可以帮您：① 解析自然语言选址需求，自动匹配行业门类并给出约束建议；"
        "② 解释任意指标含义；③ 介绍算法选型。"
        f"当前{'已接入大模型增强' if settings.LLM_ENABLED else '为规则解析模式（未配置大模型 Key）'}，"
        "选址计算全部基于真实规划数据。"
    )
