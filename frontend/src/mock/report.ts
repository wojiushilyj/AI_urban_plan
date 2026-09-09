/**
 * 报告文本 mock 生成（模块 7）。
 * 模板化填空：场景、候选 Top-N、综合得分、约束合规结论、建议。
 */
import type { ReportDoc } from '../types/report'
import type { ScenarioDetail } from '../types/scenario'
import type { SelectionResponse } from '../types/selection'

export function mockGenerateReport(
  scenario: ScenarioDetail,
  result: SelectionResponse,
  params: { grid_size_m: number; top_n: number; algorithm: string }
): ReportDoc {
  const top = result.candidates[0]
  const now = new Date().toLocaleString('zh-CN')
  return {
    title: `${scenario.name}选址分析报告（样例）`,
    generatedAt: now,
    scenarioName: scenario.name,
    sampleData: true,
    sections: [
      {
        title: '一、分析概述',
        content: `本报告基于多场景智慧选址系统（演示样例数据）生成。本次分析行业门类为「${scenario.name}」（${scenario.category}），采用 ${params.algorithm} 算法，网格精度 ${params.grid_size_m} 米。研究区网格化后共 ${result.total_cells.toLocaleString()} 个评价单元，经 ${scenario.constraints.length} 项硬约束一票否决过滤后，保留 ${result.available_cells.toLocaleString()} 个可利用单元（占比 ${((result.available_cells / result.total_cells) * 100).toFixed(1)}%）。`,
      },
      {
        title: '二、约束条件',
        content: `本次分析启用的硬约束包括：${scenario.constraints.map((c) => `${c.name}${c.buffer_m ? `（缓冲 ${c.buffer_m}m）` : ''}`).join('、')}。全部候选地块均已通过上述约束校验，不涉及永久基本农田、生态保护红线等禁限区域。`,
      },
      {
        title: '三、候选地块推荐',
        content: result.candidates
          .map(
            (c) =>
              `第 ${c.rank} 名：综合得分 ${c.score} 分，面积约 ${c.area_ha} 公顷。${c.notes}。`
          )
          .join('\n'),
      },
      {
        title: '四、结论与建议',
        content: `综合 ${scenario.factors.length} 项评价指标，推荐优先开展 ${top ? `排名第 1 的候选地块（得分 ${top.score}）` : '候选地块'} 的现场踏勘与用地预审。建议后续结合实地核查、控制性详细规划及用地报批程序推进。${result.message}`,
      },
      {
        title: '五、数据说明',
        content: '本报告全部数据为竞赛演示用样例数据（SAMPLE），不代表真实国土空间数据。正式应用时将对接国土空间规划"一张图"实施监督信息系统。',
      },
    ],
  }
}
