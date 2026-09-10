"""AI 需求解析与对话接口。规则版为主，LLM 为可选增强（见 services/ai_parse.py）。"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.ai_parse import chat_reply, parse_requirement

router = APIRouter(tags=["AI 需求交互"])


class ParseRequest(BaseModel):
    text: str = Field(default="", description="用户自然语言选址需求")


class ChatRequest(BaseModel):
    history: list[dict[str, Any]] = Field(default_factory=list)
    text: str = Field(default="")


@router.post("/ai/parse")
def api_parse(req: ParseRequest):
    """解析自然语言需求 → 行业门类 + 约束建议 + 权重 + 用地规模。"""
    return parse_requirement(req.text)


@router.post("/ai/chat")
def api_chat(req: ChatRequest):
    """选址相关问答（确定性 FAQ）。"""
    return chat_reply(req.history, req.text)
