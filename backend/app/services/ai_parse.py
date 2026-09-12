"""
AI 需求解析与对话（规则版为基线，LLM 可选增强）。

设计原则（README 铁律）：**无 LLM Key 时必须可跑通全流程**。
因此解析主逻辑是确定性的关键词 + 正则，LLM 仅在配置开启时用于语义增强。

接入 DeepSeek 后（`backend/.env` 配好 LLM_* 四项即可）：
  · `parse_requirement` —— 规则给出基线结果，LLM 可修正行业门类、补齐面积、润色结论；
    LLM 输出一律经合法性校验（门类必须在场景模板内、面积必须落在合理区间），
    且**确定性换算优先于模型猜测**（规则已解析出面积时不采信 LLM 的数值）。
  · `chat_reply` —— 由 LLM 接管自然语言问答；未配置或调用失败时回退确定性 FAQ。
两种模式下返回结构完全一致，前端无需改动。

换算口径与前端 `frontend/src/utils/area.ts` 保持一致（1 公顷 = 15 亩 = 10000 m²）。
"""
from __future__ import annotations

import re
from typing import Any

from app.config import settings
from app.services import llm
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
# 大模型提示词（仅在配置了 Key 时使用；内容即业务事实口径，防止模型臆造）
# --------------------------------------------------------------------------- #

# 对话助手的系统提示：把项目真实口径喂给模型，避免它编造图层名或数字
_CHAT_SYSTEM = (
    "你是「多场景智慧选址系统」的内置助手，服务于国土空间规划选址业务。"
    "回答必须严格基于下列事实，不得编造：\n"
    "【研究区】广西桂林市临桂区。\n"
    "【数据】真实国土空间规划图层，共 18 个图层（含生态保护红线、永久基本农田、"
    "城镇开发边界、现状建筑、控规工业用地图斑、道路、居民点等）。\n"
    "【面积换算】1 公顷 = 15 亩 = 10 000 平方米。\n"
    "【量算坐标系】CGCS2000 3 度带 37 带（EPSG:4525），距离用米、面积用公顷。\n"
    "【硬约束】布尔一票否决：永久基本农田、生态保护红线等命中即剔除；带缓冲的约束"
    "（河湖管理范围 30m、高速/铁路保护距离 100m、居民点安全距离 300~500m 等）先做缓冲再判定；"
    "库中没有对应图层的约束会被如实跳过，并在结果说明中列明。\n"
    "【权重】由「选址偏好」三档（在意 / 一般 / 不在意，基值 5/3/1）决定，"
    "归一化为 5 个维度：城市规划、交通物流、产业协同、基础配套、建造成本，权重和恒为 1。\n"
    "【算法】TOPSIS（逼近理想解排序，演示推荐）、多元回归、K-Means 聚类。\n"
    "【用地规模】需求中提到的面积会换算为公顷作为目标规模，按 ±50% 容差筛选候选地块；"
    "该容差为初值，最终由算法设计人员按行业门类核定。\n"
    "【报告导出】支持 PDF（打印）、Excel（权重与候选表）、图纸图片三种格式。\n"
    "回答要求：中文、口语化、分点清晰，控制在 3~5 句；只回答选址业务相关问题，"
    "无关话题礼貌拒答；事实不明或数据未覆盖时直接说明「该项不在当前数据范围内」。"
)

_PARSE_SCHEMA_HINT = (
    '{"scenarioId": "上述 id 之一", "targetAreaHa": 数字或 null, '
    '"explanation": "一句话说明解析结论（中文，不超过 60 字）"}'
)


def _parse_system_prompt() -> str:
    """需求解析提示词：动态注入行业门类清单，保证模型只能选合法 id。"""
    catalog = "；".join(f"{s['id']}={s['name']}" for s in SCENARIOS.values())
    return (
        "你是国土空间规划选址需求解析器，负责把用户的自然语言选址需求解析为 JSON。\n"
        f"可选行业门类（scenarioId 只能取下列 id 之一）：{catalog}。\n"
        "面积换算：1 公顷 = 15 亩 = 10 000 平方米；用户未提及用地规模时 targetAreaHa 取 null。\n"
        "只输出一个 JSON 对象，不要解释文字、不要代码块标记。字段：\n"
        + _PARSE_SCHEMA_HINT
    )


def _llm_parse(text: str) -> dict[str, Any] | None:
    """调用大模型解析需求；失败返回 None。"""
    return llm.chat_json(
        [
            {"role": "system", "content": _parse_system_prompt()},
            {"role": "user", "content": text.strip()[:1000]},
        ],
        temperature=0.1,   # 解析任务要稳定，温度压到最低
        # 推理模型的思考同样占用输出预算，预算不足会导致正文为空而静默回退规则版，
        # 故此处取配置项（默认 2048），详见 config.py 中 LLM_MAX_TOKENS_PARSE 的说明。
        max_tokens=settings.LLM_MAX_TOKENS_PARSE,
        timeout=settings.LLM_TIMEOUT_S,
    )


_MAX_HISTORY = 8      # 只回传最近若干轮，控制 token 与响应时延
_MAX_CHARS = 1500     # 单条消息截断上限


def _llm_chat(history: list[dict[str, Any]], q: str) -> str | None:
    """调用大模型进行对话；失败返回 None（调用方回退 FAQ）。"""
    messages: list[dict[str, str]] = [{"role": "system", "content": _CHAT_SYSTEM}]
    for item in (history or [])[-_MAX_HISTORY:]:
        if not isinstance(item, dict):
            continue
        role, content = item.get("role"), item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content.strip()[:_MAX_CHARS]})
    # 避免把当前提问重复追加（前端可能已把它放进 history 末尾）
    if messages[-1].get("content") != q[:_MAX_CHARS]:
        messages.append({"role": "user", "content": q[:_MAX_CHARS]})
    return llm.chat(
        messages,
        temperature=0.5,
        max_tokens=settings.LLM_MAX_TOKENS_CHAT,
        timeout=settings.LLM_TIMEOUT_S,
    )


# --------------------------------------------------------------------------- #
# 需求解析
# --------------------------------------------------------------------------- #

def parse_requirement(text: str) -> dict[str, Any]:
    """自然语言选址需求 → 行业门类 + 约束建议 + 权重 + 用地规模。

    规则解析是**基线**（无 Key、未联网、模型报错时都必须给出完整结果），
    配置 Key 后由 LLM 做语义增强；模型输出全部经校验，不合法即忽略。
    """
    text = text or ""
    matched = [kw for kws, _ in KEYWORD_MAP for kw in kws if kw in text]

    # ---- 基线：关键词定位行业门类 + 正则抽取用地规模 ----
    scenario_id = DEFAULT_SCENARIO_ID
    for kws, sid in KEYWORD_MAP:
        if any(kw in text for kw in kws):
            scenario_id = sid
            break
    area: dict[str, Any] | None = parse_area_requirement(text)
    explanation: str | None = None

    # ---- 可选增强：大模型语义解析（仅 LLM_ENABLED=true 且 Key 齐全时触发）----
    llm_enhanced = False
    if llm.llm_available() and text.strip():
        data = _llm_parse(text)
        if data:
            llm_sid = str(data.get("scenarioId") or "").strip()
            if llm_sid in SCENARIOS:
                scenario_id = llm_sid
                llm_enhanced = True

            # 面积：规则已确定性换算时以规则为准，规则未命中才采信模型的数值
            ha = data.get("targetAreaHa")
            if area is None and isinstance(ha, (int, float)) and not isinstance(ha, bool):
                ha = float(ha)
                if MIN_HA <= ha <= MAX_HA:
                    area = {
                        "target_ha": round(ha, 2),
                        "text": f"{round(ha, 2)} 公顷",
                        "unit": "公顷",
                        "value": round(ha, 2),
                    }
                    llm_enhanced = True

            exp = data.get("explanation")
            if isinstance(exp, str) and exp.strip():
                explanation = exp.strip().replace("\n", " ")[:200]
                llm_enhanced = True

    scenario = SCENARIOS[scenario_id]
    weights = dict(scenario["weights_ahp"])
    total = sum(weights.values()) or 1.0
    weights = {k: round(v / total, 2) for k, v in weights.items()}

    # 硬约束全部建议启用（required 为不可关闭项，其余按门类默认建议）
    constraints = [c["id"] for c in scenario["constraints"]]

    if explanation is None:
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
        # 前端可据此提示「本次结论由大模型增强」；规则模式恒为 false
        "llmEnhanced": llm_enhanced,
    }


# --------------------------------------------------------------------------- #
# 对话（配置了 Key 时由大模型接管；否则回退确定性 FAQ）
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
    """对话回复。

    配置了大模型 Key → 由 LLM 接管（系统提示词已注入项目事实口径）；
    未配置或调用失败 → 回退确定性 FAQ，保证演示不中断。
    """
    q = text or ""
    if not q.strip() and history:
        q = str(history[-1].get("content", ""))
    q = q.strip()
    if not q:
        return "请描述您的选址需求，例如「为装备制造项目寻找连片用地，约 20 公顷」。"

    # 1) 大模型接管（可选增强）
    if llm.llm_available():
        reply = _llm_chat(history, q)
        if reply:
            return reply

    # 2) 回退：确定性 FAQ
    for keys, answer in _FAQ:
        if any(k in q for k in keys):
            return answer
    return (
        "收到您的需求。我可以帮您：① 解析自然语言选址需求，自动匹配行业门类并给出约束建议；"
        "② 解释任意指标含义；③ 介绍算法选型。"
        f"当前{'已接入大模型增强' if settings.LLM_ENABLED else '为规则解析模式（未配置大模型 Key）'}，"
        "选址计算全部基于真实规划数据。"
    )
