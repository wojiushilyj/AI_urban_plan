/**
 * 偏好学习模型 mock（模块 8.1）。
 *
 * mock 模式下 `/api/ai/model` 返回本文件内置的「机器学习模式」演示模型：
 * 让「AI 偏好学习」页签在未接入后端时也能完整展示
 * 交叉验证 AUC / 训练样本 / 学习权重对比 / 消融实验等机器学习内容。
 *
 * ⚠️ 以下指标为演示数值（合理量级），接入真实后端后由
 * backend/app/services/ai_model.py 的实际训练结果替代。
 */
import type { AiModelInfo } from '../api/ai'

const FEATURE_LABELS: Record<string, string> = {
  urban_planning: '城市规划',
  transport: '交通物流',
  industry: '产业协同',
  infrastructure: '基础配套',
  cost: '建造成本',
}

export function mockGetAiModel(): AiModelInfo {
  return {
    available: true,
    algo: 'LogisticRegression（逻辑回归，5 折分层交叉验证）',
    task: '二分类：控规工业地块是否已被实际开发',
    samples: 268,
    positives: 43,
    negatives: 225,
    positive_rate: 0.16,
    features: Object.keys(FEATURE_LABELS),
    feature_labels: FEATURE_LABELS,
    coefficients: {
      urban_planning: 0.62,
      transport: 0.94,
      industry: 0.51,
      infrastructure: 0.73,
      cost: -0.48,
    },
    metrics: {
      auc_mean: 0.712,
      auc_std: 0.038,
      acc_mean: 0.784,
      folds: [0.72, 0.69, 0.74, 0.68, 0.73],
    },
    ablation: {
      全部因子: { n_features: 5, features: Object.keys(FEATURE_LABELS), auc: 0.712, auc_std: 0.038, acc: 0.784 },
      去除交通物流: { n_features: 4, features: ['urban_planning', 'industry', 'infrastructure', 'cost'], auc: 0.641, auc_std: 0.045, acc: 0.751 },
      去除基础配套: { n_features: 4, features: ['urban_planning', 'transport', 'industry', 'cost'], auc: 0.663, auc_std: 0.041, acc: 0.762 },
      去除城市规划: { n_features: 4, features: ['transport', 'industry', 'infrastructure', 'cost'], auc: 0.678, auc_std: 0.043, acc: 0.768 },
      去除产业协同: { n_features: 4, features: ['urban_planning', 'transport', 'infrastructure', 'cost'], auc: 0.695, auc_std: 0.04, acc: 0.775 },
      去除建造成本: { n_features: 4, features: ['urban_planning', 'transport', 'industry', 'infrastructure'], auc: 0.702, auc_std: 0.039, acc: 0.779 },
    },
    univariate_auc: {
      urban_planning: 0.598,
      transport: 0.651,
      industry: 0.567,
      infrastructure: 0.62,
      cost: 0.553,
    },
    /** 学习到的 5 维权重（由逻辑回归系数归一化，和为 1） */
    learned_weights: {
      urban_planning: 0.18,
      transport: 0.29,
      industry: 0.17,
      infrastructure: 0.2,
      cost: 0.16,
    },
    /** 数据泄漏规避说明 */
    leakage_note: '开发状态标签的判定年份晚于各因子统计年份，特征与标签无时间重叠，规避数据泄漏。',
  }
}
