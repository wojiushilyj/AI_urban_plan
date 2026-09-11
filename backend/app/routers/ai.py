"""AI 能力接口：需求解析、对话、偏好学习模型。"""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_model import MODEL_FEATURE_IDS, _build_samples, learn_preference_weights
from app.services.ai_parse import chat_reply, parse_requirement

router = APIRouter(tags=["AI 能力"])


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


@router.get("/ai/model")
def api_model():
    """
    偏好学习模型：评估指标、学习权重、消融实验、单特征 AUC。

    模型以「控规工业地块是否已被实际开发」为标签（现状工业用地覆盖 > 5%），
    从真实开发事实中反推区位偏好权重。含完整的**数据泄漏审计**与能力边界声明，
    详见 `backend/app/services/ai_model.py` 顶部文档。
    """
    # 数据未就绪时返回 available=false（HTTP 200），前端据此刻度降级
    return learn_preference_weights()


@router.get("/ai/model/parcels")
def api_model_parcels(limit: int = 20):
    """模型训练样本明细，供前端散点图等可视化。"""
    limit = max(1, min(limit, 200))
    try:
        X, y, meta, _ = _build_samples()
    except Exception as e:  # noqa: BLE001 — 数据缺失给出可读原因
        raise HTTPException(status_code=503, detail=f"训练样本不可用：{e}")

    if X.shape[0] == 0:
        return {"items": [], "total": 0, "features": MODEL_FEATURE_IDS}

    idx = {f: i for i, f in enumerate(MODEL_FEATURE_IDS)}
    items = [
        {
            "code": m["code"],
            "label": int(y[i]),
            "area_ha": m["area_ha"],
            "overlap": m["overlap"],
            "nb_density": m.get("nb_density"),
            "features": {f: round(float(X[i, idx[f]]), 2) for f in MODEL_FEATURE_IDS},
        }
        for i, m in enumerate(meta[:limit])
    ]
    return {
        "items": items,
        "total": int(X.shape[0]),
        "positives": int(y.sum()),
        "features": MODEL_FEATURE_IDS,
    }
