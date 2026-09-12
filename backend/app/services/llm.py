"""
大模型客户端（DeepSeek / 任意 OpenAI 兼容接口）。

设计铁律（与 README 一致）：**无 Key 或调用失败时，主流程必须照常跑通**。
因此本模块对外函数一律不抛异常 —— 网络、鉴权、限流、格式等任何失败都返回 None，
由调用方（`app/services/ai_parse.py`）回退到确定性规则版。

配置在 `backend/.env`（该文件已被 .gitignore 忽略，Key 不会进仓库）：

    LLM_ENABLED=true
    LLM_BASE_URL=https://api.deepseek.com
    LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
    LLM_MODEL=deepseek-chat

⚠️ Key 只允许存在于服务端。前端产物（dist）是公开 JS，
   任何写进 `frontend/.env*` 的密钥都会被任意访客读取。

⚠️ httpx 默认读取 HTTP_PROXY / HTTPS_PROXY / ALL_PROXY 环境变量。
   国内服务器直连 api.deepseek.com 即可；若服务器上残留了系统代理，
   调用会被转发到代理而失败（表现为 502 upstream connect failed），
   此时清空上述环境变量即可，或改用直连地址。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# DeepSeek 官方口径的缺省值（`.env` 里只填 Key 也能跑起来）
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

# 演示场景下的等待上限：宁可回退规则版，也不让界面长时间空转。
# 取值来自 config.py（默认 60s）——推理模型的思考耗时波动较大，留足余量。
TIMEOUT_S = settings.LLM_TIMEOUT_S
# 失败重试次数（不含首次）。重试 1 次足以穿透偶发抖动，又不至于拖长响应
MAX_RETRIES = 1


def llm_available() -> bool:
    """是否具备真实调用条件：开关开启 + 地址/Key/模型名三者齐全。"""
    return bool(
        settings.LLM_ENABLED
        and (settings.LLM_API_KEY or "").strip()
        and (settings.LLM_BASE_URL or "").strip()
        and (settings.LLM_MODEL or "").strip()
    )


def _endpoint() -> str:
    """拼接 chat/completions 端点，兼容 base 末尾带 `/` 或 `/v1` 的写法。"""
    base = (settings.LLM_BASE_URL or DEFAULT_BASE_URL).strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def chat(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    timeout: float = TIMEOUT_S,
) -> str | None:
    """调用大模型返回纯文本；任何失败均返回 None（调用方须回退规则版）。"""
    if not llm_available():
        return None

    payload = {
        "model": (settings.LLM_MODEL or DEFAULT_MODEL).strip(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {(settings.LLM_API_KEY or '').strip()}",
        "Content-Type": "application/json",
    }
    url = _endpoint()

    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                # 只截取前 200 字符，避免把凭据等敏感信息写进日志
                logger.warning("大模型返回 HTTP %s：%s", resp.status_code, resp.text[:200])
                continue
            data = resp.json()
            content = (
                (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            ).strip()
            if content:
                return content
            logger.warning("大模型返回内容为空")
        except Exception as exc:  # noqa: BLE001 —— 任何异常都不允许打断主流程
            logger.warning("大模型调用异常（第 %s 次尝试）：%s", attempt + 1, exc)

    return None


_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.S)


def chat_json(messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any] | None:
    """要求模型输出 JSON 对象；解析失败返回 None。

    模型偶尔会裹上 ```json 围栏或前后带解释文字，这里做两轮容错提取。
    """
    text = chat(messages, **kwargs)
    if not text:
        return None

    cleaned = _FENCE_RE.sub("", text.strip())
    candidates = [cleaned]
    block = _JSON_BLOCK_RE.search(cleaned)
    if block:
        candidates.append(block.group(0))

    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj

    logger.warning("大模型输出不是合法 JSON：%s", text[:200])
    return None
