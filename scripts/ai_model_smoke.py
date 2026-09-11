"""
AI 偏好学习模型自测（无需启动服务）。

用法：
    <venv>/Scripts/python.exe scripts/ai_model_smoke.py

输出：样本构成、交叉验证指标、消融实验、单特征 AUC、特征系数、学习权重、
      以及数据泄漏审计的关键结论。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.ai_model import MODEL_FEATURE_IDS, learn_preference_weights  # noqa: E402

PASS, FAIL = [], []


def check(name: str, cond: bool, extra: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  {extra}" if extra else ""))


def main() -> int:
    t0 = time.perf_counter()
    r = learn_preference_weights()
    dt = (time.perf_counter() - t0) * 1000

    print("=" * 72)
    print(f"AI 偏好学习模型自测（训练 + 消融，耗时 {dt:.0f} ms）")
    print("=" * 72)

    if not r.get("available"):
        print(f"✗ 模型不可用：{r.get('reason')}")
        return 1

    m = r["metrics"]
    print(f"\n模型：{r['algo']}")
    print(f"任务：{r['task']}")
    print(f"样本：{r['samples']}（正 {r['positives']} / 负 {r['negatives']}，"
          f"正例率 {r['positive_rate']}）")
    print(f"特征：{', '.join(r['feature_labels'][f] for f in r['features'])}")

    print("\n--- 交叉验证 ---")
    print(f"  AUC {m['auc_mean']} ± {m['auc_std']}   准确率 {m['acc_mean']}")
    print(f"  各折 AUC: {m['folds']}")
    check("AUC 高于随机基线 0.5", m["auc_mean"] > 0.5, str(m["auc_mean"]))
    check("AUC 未超过 0.98（防虚高/泄漏）", m["auc_mean"] < 0.98, str(m["auc_mean"]))

    print("\n--- 消融实验 ---")
    for name, a in r["ablation"].items():
        print(f"  {name:28s} {a['n_features']} 特征  AUC {a['auc']:.3f} ±{a['auc_std']:.3f}")
    print(f"  {'随机基线':28s} 0 特征  AUC {0.5:.3f}")
    check("消融实验至少 3 组", len(r["ablation"]) >= 3, str(len(r["ablation"])))

    print("\n--- 单特征 AUC ---")
    for k, v in r["univariate_auc"].items():
        print(f"  {r['feature_labels'][k]:10s} {v:.3f}")

    print("\n--- 标准化系数（正 = 越高越可能被开发）---")
    for k, v in r["coefficients"].items():
        print(f"  {r['feature_labels'][k]:10s} {v:+.4f}")

    print("\n--- 学习到的 5 维权重 ---")
    for k, v in r["learned_weights"].items():
        print(f"  {k:18s} {v:.4f}")

    print("\n--- 已开发 vs 未开发 组间均值 ---")
    for k, g in r["group_contrast"].items():
        print(f"  {g['label']:10s} 已开发 {g['developed_mean']:5.1f}  "
              f"未开发 {g['undeveloped_mean']:5.1f}  差 {g['diff']:+5.1f}")

    print("\n--- 泄漏审计 ---")
    print(f"  {r['leakage_note']}")
    check("特征不含 cost（其定义含建筑密度，与标签定义性相关）",
          "cost" not in r["features"], str(r["features"]))
    check("权重和为 1", abs(sum(r["learned_weights"].values()) - 1) < 0.01)
    check("负系数维度未被赋正权重",
          all(r["learned_weights"][f] == 0 or r["coefficients"][f] >= 0
              for f in r["features"] if f in r["learned_weights"]))
    check("特征名与模型声明一致",
          set(r["features"]).issubset(set(MODEL_FEATURE_IDS) | set(r["features"])))

    print("\n" + "=" * 72)
    print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
    if FAIL:
        print("失败项：" + "、".join(FAIL))
    print("=" * 72)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
