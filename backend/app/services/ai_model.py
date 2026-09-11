"""
AI 偏好学习模型：从真实开发事实中反推区位偏好权重。

## 任务定义

| 项 | 内容 |
|---|---|
| 样本 | 控规工业用地 `regulated-industrial` 145 个地块 |
| 标签 | 该地块**是否已被实际开发**（与现状工业用地 `current-industrial-land` 的重叠率 > 5% → 1，否则 0） |
| 实测 | 66 正 / 79 负（比例 45.5% / 54.5%） |
| 模型 | L2 正则逻辑回归（numpy 自研，零新增依赖） |
| 验证 | 5 折**分层**交叉验证，报告 AUC 与准确率 |

**业务含义**：控规（图纸）画了一批工业用地，但现实中只有一部分被真正开发了。
模型从「哪些地块被优先开发」这一事实中，反推出**规划实践里真正起作用的区位偏好**，
从而把规划师的隐性经验显性化为可复核的权重。

## ⚠️ 关键设计：为什么特征里没有「建造成本」因子

成本因子的正式定义含**现状建筑占地率**（拆迁成本代理，见 `features.py`）。
而标签是「是否已开发」—— 已开发的地块必然有建筑，两者**定义性相关**。
若把含建筑密度的 cost 作为特征，会得到虚高的 AUC，但模型学到的只是
「有房子 ⇒ 有房子」，毫无预测意义。这就是典型**数据泄漏**。

因此本模型：

- **训练特征** = 4 个规划因子（城市规划 / 交通物流 / 产业协同 / 基础配套）
  + 1 个空间邻域特征（`nb_score`，k=5 最近邻因子均值，体现空间集聚效应）
- **cost 维度**不参与训练，其权重在合成时**沿用 AHP 专家权重**（按相对强度折算）

这一规避决策本身即是可解释 AI 的体现：**宁可 AUC 低一点，也不要一个作弊的模型。**

## ⚠️ 泄漏审计（本模型最关键的设计决策）

初版曾把两个「看起来合理」的特征放进模型，实测发现都是泄漏，已剔除：

| 特征 | 问题 | 处理 |
|---|---|---|
| 产业协同（用**现状**工业用地算集聚距离） | 标签来源就是「与现状工业用地的重叠率」，距离≈0 即等价于已开发 | 参照图层改回**总规**工业用地（与现状层空间重叠仅 28%，非泄漏） |
| 建造成本（含**本地块**现状建筑占地率） | 有建筑 ⇔ 已开发，定义性相关 | cost 维度不参与训练，权重沿用 AHP |
| 空间邻域聚集（k=5 邻域因子均值） | 无泄漏，但消融实验显示**未带来增益**（AUC 0.649 vs 0.640） | 剔除，工具函数保留备用 |
| **周边建成度**（500m **环形**邻域建筑占地率） | 必须扣除地块自身，否则自己的建筑被算进环带 | 用 `buffer.difference(地块)` 取**环带**，单特征 AUC **0.735** ✅ |

**教训**：带泄漏的版本 AUC 0.957，修正后掉到 0.640 —— 高 AUC 全是作弊来的。
宁可报告一个诚实的 0.69，也不要一个漂亮的假指标。

## 模型能力边界（必须在申报书/答辩中如实说明）

- 样本仅 **145 个控规工业地块**（受限于临桂区控规工业用地总量），交叉验证 AUC **约 0.69**，
  折间波动 ±0.09。**该模型用于提供数据侧的权重参照，不作为选址的最终依据。**
- 规划因子对本区实际开发结果的解释力有限（AUC 0.64），说明实际开发还受供地节奏、
  招商政策、产权等**非空间因素**主导 —— 这本身是有价值的结论：选址不能只看图纸因子。
- 权重来源仍以**专家 AHP + 熵权**为默认；AI 学习权重作为**对照与可选方案**呈现。

## 复现方式

    <venv>/Scripts/python.exe scripts/ai_model_smoke.py
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
from shapely.geometry import Point
from shapely.strtree import STRtree

from app.services import spatial
from app.services.features import (
    FACTOR_IDS,
    city_context,
    neighborhood_score,
    polsby_popper,
)

# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #

POOL_LAYER = "regulated-industrial"          # 候选池 / 学习样本
LABEL_LAYER = "current-industrial-land"      # 标签来源：现状工业用地

NB_K = 5                 # 邻域特征取最近 k 个地块
DEV_THRESHOLD = 0.05     # 重叠率 > 5% 即视为「已开发」
L2 = 0.10                # L2 正则强度
LR = 0.50                # 学习率
EPOCHS = 3000            # 迭代轮数
N_FOLDS = 5
SEED = 42

MODEL_FEATURE_IDS = ["urban_planning", "transport", "industry",
                     "infrastructure", "nb_density"]
MODEL_FACTOR_IDS = ["urban_planning", "transport", "industry", "infrastructure"]

FEATURE_LABEL = {
    "urban_planning": "城市规划",
    "transport": "交通物流",
    "industry": "产业协同",
    "infrastructure": "基础配套",
    "nb_score": "空间邻域聚集",
    "nb_density": "周边建成度",
}

# 消融实验组合：用于如实报告各特征的实际贡献，避免「堆特征刷指标」
# 注意：所有组合的特征都必须是 MODEL_FEATURE_IDS 的子集，否则会被静默丢弃
ABLATION_COMBOS: dict[str, list[str]] = {
    "仅 4 个规划因子": ["urban_planning", "transport", "industry", "infrastructure"],
    "仅 周边建成度": ["nb_density"],
    "主模型：4 因子 + 周边建成度": MODEL_FEATURE_IDS,
}

RANDOM_BASELINE_AUC = 0.5   # 随机猜测基线，用于对照

NB_DENSITY_RADIUS_M = 500.0     # 邻域建成度环带半径


# --------------------------------------------------------------------------- #
# 基础算法（自研，避免引入 scikit-learn 等重型依赖）
# --------------------------------------------------------------------------- #

def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


def _standardize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    return (X - mean) / std, mean, std


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    """
    AUC（ROC 曲线下面积），基于 Mann-Whitney U 统计量，**含并列秩处理**。
    取值 0.5 = 随机猜测，1.0 = 完美区分。
    """
    y = np.asarray(y)
    p = np.asarray(p)
    pos, neg = p[y == 1], p[y == 0]
    if pos.size == 0 or neg.size == 0:
        return float("nan")

    order = np.argsort(p, kind="mergesort")
    sp = p[order]
    ranks = np.empty(p.size, dtype=float)
    i = 0
    while i < sp.size:                      # 并列值取平均秩
        j = i
        while j + 1 < sp.size and sp[j + 1] == sp[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1

    r_pos = ranks[y == 1].sum()
    n1, n0 = pos.size, neg.size
    return float((r_pos - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def train_logistic(
    X: np.ndarray, y: np.ndarray,
    l2: float = L2, lr: float = LR, epochs: int = EPOCHS,
) -> tuple[np.ndarray, float]:
    """全批量梯度下降训练 L2 正则逻辑回归。返回 (系数, 截距)。"""
    m, n = X.shape
    w = np.zeros(n)
    b = 0.0
    for _ in range(epochs):
        p = _sigmoid(X @ w + b)
        g = p - y
        w -= lr * (X.T @ g / m + l2 * w)
        b -= lr * float(g.mean())
    return w, b


def _stratified_folds(y: np.ndarray, k: int, seed: int) -> list[np.ndarray]:
    """分层 K 折：保证每折正负比例与总体一致（小样本下尤为重要）。"""
    rng = np.random.default_rng(seed)
    folds = [[] for _ in range(k)]
    for cls in (1, 0):
        idx = np.flatnonzero(y == cls)
        rng.shuffle(idx)
        for i, j in enumerate(idx):
            folds[i % k].append(int(j))
    return [np.array(sorted(f)) for f in folds]


def cross_validate(X: np.ndarray, y: np.ndarray, k: int = N_FOLDS,
                   seed: int = SEED) -> dict[str, Any]:
    """分层 K 折交叉验证。标准化参数只从训练折估计，避免测试信息泄漏。"""
    folds = _stratified_folds(y, k, seed)
    aucs, accs = [], []
    for i in range(k):
        test = folds[i]
        train = np.concatenate([folds[j] for j in range(k) if j != i])
        Xtr, mu, sd = _standardize(X[train])
        Xte = (X[test] - mu) / sd
        w, b = train_logistic(Xtr, y[train])
        p = _sigmoid(Xte @ w + b)
        aucs.append(_auc(y[test], p))
        accs.append(float(((p >= 0.5) == y[test]).mean()))
    return {
        "auc_mean": round(float(np.nanmean(aucs)), 3),
        "auc_std": round(float(np.nanstd(aucs)), 3),
        "acc_mean": round(float(np.nanmean(accs)), 3),
        "folds": [round(a, 3) for a in aucs],
    }


# --------------------------------------------------------------------------- #
# 样本构建
# --------------------------------------------------------------------------- #

def _build_samples() -> tuple[np.ndarray, np.ndarray, list[dict], list[Point]]:
    """构建特征矩阵 X、标签 y，以及每块地的元信息与投影质心。"""
    pool_ll = spatial.load_layer(POOL_LAYER)
    pool_pj = spatial.load_layer_projected(POOL_LAYER)
    label_pj = spatial.load_layer_projected(LABEL_LAYER)

    label_geoms = [g.buffer(0) for g in label_pj.geometry]
    label_tree = STRtree(label_geoms)

    ctx = city_context()
    rows: list[list[float]] = []
    meta: list[dict] = []
    centroids: list[Point] = []
    ring_density: list[float] = []
    y: list[int] = []

    for i, (g_ll, g_pj) in enumerate(zip(pool_ll.geometry, pool_pj.geometry), start=1):
        if g_ll is None or g_ll.is_empty or g_pj is None or g_pj.is_empty:
            continue
        g_pj = g_pj.buffer(0)
        pt = g_pj.representative_point()
        area_ha = g_pj.area / 1e4
        regularity = polsby_popper(g_pj)
        f = ctx.factors(g_pj, pt, area_ha, regularity)

        # 标签：与现状工业用地的重叠率
        covered = 0.0
        for j in label_tree.query(g_pj, predicate="intersects"):
            try:
                covered += g_pj.intersection(label_geoms[int(j)]).area
            except Exception:
                continue
        ratio = covered / g_pj.area if g_pj.area > 0 else 0.0

        rows.append([f[k] for k in MODEL_FACTOR_IDS])
        meta.append({
            "code": f"KG-{i:03d}",
            "area_ha": round(area_ha, 2),
            "regularity": round(regularity, 3),
            "overlap": round(ratio, 3),
            "factors": {k: f[k] for k in FACTOR_IDS},
            "density": round(f["_debug"]["density"], 3),
        })
        centroids.append(pt)
        ring_density.append(ctx.neighborhood_density(g_pj, NB_DENSITY_RADIUS_M))
        y.append(1 if ratio > DEV_THRESHOLD else 0)

    base = np.array(rows, dtype=float)
    if base.size == 0:
        return np.zeros((0, len(MODEL_FEATURE_IDS))), np.zeros(0, dtype=int), [], []

    # ⚠️ X 的列顺序必须与 MODEL_FEATURE_IDS 严格一致，否则消融/系数会张冠李戴。
    nb = neighborhood_score(base, np.array([[p.x, p.y] for p in centroids]), k=NB_K)
    assert len(MODEL_FEATURE_IDS) == base.shape[1] + 1, "特征名与特征矩阵列数不一致"
    X = np.column_stack([base, np.array(ring_density)])
    for m, v, rd in zip(meta, nb, ring_density):
        m["nb_score"] = round(float(v), 1)       # 仅作参考记录，不进入模型
        m["nb_density"] = round(float(rd), 3)
    return X, np.array(y, dtype=int), meta, centroids


# --------------------------------------------------------------------------- #
# 训练入口（进程内缓存）
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def learn_preference_weights() -> dict[str, Any]:
    """
    训练偏好模型并返回学到的权重与评估指标。

    返回结构见 docs/SCENARIOS.md；前端 `GET /api/ai/model` 直接消费。
    结果按进程缓存 —— 训练约百毫秒量级，但没必要每次请求重跑。
    """
    X, y, meta, _ = _build_samples()
    if X.shape[0] < 20 or y.sum() == 0 or (y == 0).sum() == 0:
        return {"available": False, "reason": "样本不足或标签单一，无法训练"}

    metrics = cross_validate(X, y)

    # 消融实验：如实报告各特征组合的实际贡献
    idx = {f: i for i, f in enumerate(MODEL_FEATURE_IDS)}
    ablation = {}
    all_cols = set()
    for name, feats in ABLATION_COMBOS.items():
        cols = [idx[f] for f in feats if f in idx]
        all_cols.update(cols)
        m = cross_validate(X[:, cols], y)
        ablation[name] = {
            "n_features": len(cols),
            "features": feats,
            "auc": m["auc_mean"],
            "auc_std": m["auc_std"],
            "acc": m["acc_mean"],
        }
    # 单特征 AUC（用于说明「信号在哪」）
    univariate = {}
    for f in MODEL_FEATURE_IDS:
        univariate[f] = round(float(_auc(y, X[:, idx[f]])), 3)

    # 全量训练，取系数作特征重要性（特征已标准化，|β| 可比）
    Xs, mu, sd = _standardize(X)
    w, b = train_logistic(Xs, y)

    coefs = {fid: round(float(w[i]), 4) for i, fid in enumerate(MODEL_FEATURE_IDS)}

    # ---- 权重合成 ----
    # 学习权重只覆盖 4 个规划因子；cost 维度沿用 AHP 专家权重，按相对强度折算到同一量纲。
    # ⚠️ 用 max(0, β) 而非 |β|：系数为负意味着该维度与实际开发**负相关**，
    #    若按绝对值给高权重，会与模型结论相反，属于方向性错误。
    importances = {fid: max(0.0, coefs[fid]) for fid in MODEL_FACTOR_IDS}
    total = sum(importances.values())
    if total <= 0:                       # 全部非正时退化为等权，避免权重全零
        learned = {fid: 1.0 / len(MODEL_FACTOR_IDS) for fid in MODEL_FACTOR_IDS}
    else:
        learned = {fid: importances[fid] / total for fid in MODEL_FACTOR_IDS}

    from app.services.scenarios import get_scenario
    ahp = get_scenario("B")["weights_ahp"]        # 10 门类 AHP 权重一致（各 0.2）
    ahp_others = np.mean([ahp[fid] for fid in MODEL_FACTOR_IDS]) or 1.0
    cost_strength = float(np.mean(list(importances.values()))) * (ahp["cost"] / ahp_others)

    raw = {**learned, "cost": cost_strength}
    s = sum(raw.values()) or 1.0
    weights = {k: round(v / s, 4) for k, v in raw.items()}

    # ---- 组间差异（可读性最好的解释）----
    group = {}
    for fid in MODEL_FACTOR_IDS:
        col = [m["factors"][fid] for m in meta]
        arr = np.array(col)
        group[fid] = {
            "label": FEATURE_LABEL[fid],
            "developed_mean": round(float(arr[y == 1].mean()), 1),
            "undeveloped_mean": round(float(arr[y == 0].mean()), 1),
            "diff": round(float(arr[y == 1].mean() - arr[y == 0].mean()), 1),
        }

    return {
        "available": True,
        "algo": "L2 正则逻辑回归（自研 numpy 实现）",
        "task": "预测控规工业地块是否已被实际开发，反推区位偏好权重",
        "samples": int(X.shape[0]),
        "positives": int(y.sum()),
        "negatives": int((y == 0).sum()),
        "positive_rate": round(float(y.mean()), 3),
        "features": MODEL_FEATURE_IDS,
        "feature_labels": FEATURE_LABEL,
        "coefficients": coefs,               # 标准化特征上的系数（含正负号，可解释方向）
        "normalized_feature_mean": [round(float(v), 2) for v in mu],
        "metrics": metrics,
        "ablation": ablation,                # 消融实验：各特征组合的交叉验证 AUC
        "univariate_auc": univariate,        # 单特征 AUC：信号在哪
        "learned_weights": weights,          # 用于选址打分的 5 维权重
        "leakage_note": (
            "特征中不含「建造成本」维度：其定义含现状建筑占地率，与标签（是否已开发）"
            "存在定义性相关，纳入即数据泄漏。cost 权重沿用 AHP 专家权重折算。"
        ),
        "group_contrast": group,
    }
