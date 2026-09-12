"""
大模型接入冒烟测试（DeepSeek / OpenAI 兼容）。

用法（在项目根目录）：
    backend/.venv/Scripts/python.exe scripts/llm_smoke.py

覆盖场景：
  1. 规则模式 —— LLM 关闭时，解析与对话必须给出完整结果
  2. 调用失败 —— 启用但 Key 无效/连不通时，必须**静默回退**规则版，不得抛异常
  3. 输出非法 —— 模型返回越界门类 id、超范围面积时必须被拒，不得污染结果
  4. JSON 容错 —— ```json 围栏、前后夹带解释文字都要能解析
  5. 真实调用 —— 若 .env 已配好 Key，则真发一次请求校验端到端

铁律：任何一项失败都意味着「大模型不可用时主流程可能被拖断」。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings                     # noqa: E402
from app.services import ai_parse, llm              # noqa: E402
from app.services.scenarios import SCENARIOS        # noqa: E402

PASSED = 0
FAILED = 0


def check(name: str, ok: bool, detail: object = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED += 1
        print(f"  [FAIL] {name}  -> {detail!r}")


def set_llm(enabled: bool, base: str = "", key: str = "", model: str = "") -> None:
    """直接改写运行期配置（settings 为模块级单例，改属性即生效）。"""
    settings.LLM_ENABLED = enabled
    settings.LLM_BASE_URL = base
    settings.LLM_API_KEY = key
    settings.LLM_MODEL = model


ORIG = (
    settings.LLM_ENABLED,
    settings.LLM_BASE_URL,
    settings.LLM_API_KEY,
    settings.LLM_MODEL,
)

REQUIRED_KEYS = {
    "scenarioId", "scenarioName", "matchedKeywords", "constraints",
    "weights", "explanation", "targetAreaHa", "targetAreaText", "llmEnhanced",
}

print("=" * 68)
print("大模型接入冒烟测试")
print("=" * 68)

# --------------------------------------------------------------------------- #
print("\n[1] 规则模式（LLM_ENABLED=false）")
set_llm(False)
r = ai_parse.parse_requirement("为装备制造项目寻找连片用地，占地面积约 20 公顷，物流便利")
check("返回字段完整", REQUIRED_KEYS <= set(r), sorted(REQUIRED_KEYS - set(r)))
check("门类识别为 C3 装备制造", r["scenarioId"] == "C3", r["scenarioId"])
check("面积换算为 20.0 公顷", r["targetAreaHa"] == 20.0, r["targetAreaHa"])
check("llmEnhanced 为 false", r["llmEnhanced"] is False)
check("权重归一化到两位小数", all(isinstance(v, float) for v in r["weights"].values()), r["weights"])

reply = ai_parse.chat_reply([], "权重是怎么确定的？")
check("对话走 FAQ（含 5/3/1 口径）", "5/3/1" in reply, reply[:60])

# --------------------------------------------------------------------------- #
print("\n[2] 启用但连不通（Key 无效）→ 必须静默回退")
set_llm(True, base="http://127.0.0.1:9/v1", key="sk-invalid-smoke-key", model="deepseek-chat")
check("llm_available() 为 true", llm.llm_available() is True)
r2 = ai_parse.parse_requirement("为装备制造项目寻找连片用地，约 20 公顷")
check("解析未抛异常且结果完整", r2["scenarioId"] == "C3" and r2["targetAreaHa"] == 20.0, r2)
check("已回退（llmEnhanced=false）", r2["llmEnhanced"] is False)
check("结论为规则文案", "已解析您的选址需求" in r2["explanation"], r2["explanation"][:60])
r3 = ai_parse.chat_reply([], "支持哪些算法？")
check("对话回退 FAQ", "TOPSIS" in r3, r3[:60])

set_llm(True, base="", key="", model="")
check("Key 缺失时 llm_available() 为 false", llm.llm_available() is False)

# --------------------------------------------------------------------------- #
print("\n[3] 模型输出非法 → 必须被拒，不得污染结果")
import app.services.llm as llm_mod  # noqa: E402

orig_chat_json = llm_mod.chat_json
set_llm(True, base="http://example.invalid/v1", key="k", model="m")
llm_mod.chat_json = lambda *a, **k: {                      # type: ignore[assignment]
    "scenarioId": "ZZZ",          # 不在场景模板内
    "targetAreaHa": 999999,       # 远超合理区间
    "explanation": "",
}
r5 = ai_parse.parse_requirement("为物流园区选址，约 500 亩")
check("非法门类被忽略（保持 G）", r5["scenarioId"] == "G", r5["scenarioId"])
check("越界面积被忽略（保持 33.33）", r5["targetAreaHa"] == 33.33, r5["targetAreaHa"])
check("llmEnhanced 仍为 false", r5["llmEnhanced"] is False)

llm_mod.chat_json = lambda *a, **k: {                      # type: ignore[assignment]
    "scenarioId": "I",            # 合法但规则未命中 → 应采用模型判断
    "targetAreaHa": 60,
    "explanation": "识别为信息技术服务业，建议用地 60 公顷。",
}
r6 = ai_parse.parse_requirement("我要建一个机房项目")
check("合法门类被采纳（I）", r6["scenarioId"] == "I", r6["scenarioId"])
check("规则未命中时采纳模型面积", r6["targetAreaHa"] == 60.0, r6["targetAreaHa"])
check("采纳模型结论文案", "信息技术服务" in r6["explanation"], r6["explanation"][:60])
check("llmEnhanced 为 true", r6["llmEnhanced"] is True)

llm_mod.chat_json = lambda *a, **k: {                      # type: ignore[assignment]
    "scenarioId": "G",
    "targetAreaHa": 9999,         # 规则已算出面积 → 必须以规则为准
    "explanation": "",
}
r7 = ai_parse.parse_requirement("为物流园区选址，约 500 亩")
check("规则面积优先于模型猜测", r7["targetAreaHa"] == 33.33, r7["targetAreaHa"])

# --------------------------------------------------------------------------- #
print("\n[4] JSON 容错解析")
llm_mod.chat_json = orig_chat_json   # 先还原场景 3 的替身，否则测的是替身本身
orig_chat = llm_mod.chat
llm_mod.chat = lambda *a, **k: '```json\n{"scenarioId": "G", "targetAreaHa": null}\n```'  # type: ignore[assignment]
check("能剥离 ```json 围栏", llm_mod.chat_json([]) == {"scenarioId": "G", "targetAreaHa": None})

llm_mod.chat = lambda *a, **k: '好的，结果如下：{"a": 1} 以上。'  # type: ignore[assignment]
check("能从冗余文本抽取 JSON", llm_mod.chat_json([]) == {"a": 1})

llm_mod.chat = lambda *a, **k: "抱歉，我无法完成该请求"  # type: ignore[assignment]
check("非 JSON 内容返回 None", llm_mod.chat_json([]) is None)

llm_mod.chat = lambda *a, **k: None  # type: ignore[assignment]
check("调用失败返回 None", llm_mod.chat_json([]) is None)

llm_mod.chat = orig_chat       # type: ignore[assignment]
llm_mod.chat_json = orig_chat_json  # type: ignore[assignment]

# --------------------------------------------------------------------------- #
print("\n[5] 真实调用（.env 已配置有效 Key 时才执行）")
set_llm(*ORIG)
if llm.llm_available():
    r8 = ai_parse.parse_requirement("为食品加工项目寻找地块，劳动力和交通要好，约 500 亩")
    check("真调用返回合法门类", r8["scenarioId"] in SCENARIOS, r8["scenarioId"])
    check("真调用已增强", r8["llmEnhanced"] is True, r8["explanation"][:60])
    answer = ai_parse.chat_reply([], "用地规模容差是什么意思？")
    check("对话返回非空", bool(answer and answer.strip()), answer[:60])
    print(f"\n  —— 大模型返回示例 ——\n  {answer[:200]}")
else:
    print("  [SKIP] 当前 backend/.env 未配置 Key，真调用未测试")

# --------------------------------------------------------------------------- #
print("\n" + "=" * 68)
print(f"结果：{PASSED} 项通过 / {FAILED} 项失败")
print("=" * 68)
sys.exit(1 if FAILED else 0)
