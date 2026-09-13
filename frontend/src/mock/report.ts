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
    title: `${scenario.name}选址分析报告`,
    generatedAt: now,
    scenarioName: scenario.name,
    sections: [
      {
        title: '一、分析概述',
        content: `本报告基于多场景智慧选址系统生成。本次分析行业门类为「${scenario.name}」（${scenario.category}），采用 ${params.algorithm} 算法。候选池为控规工业用地图斑 ${result.total_cells.toLocaleString()} 个，经硬约束一票否决与面积条件筛选后保留 ${result.available_cells.toLocaleString()} 个（占比 ${((result.available_cells / result.total_cells) * 100).toFixed(1)}%）。`,
      },
      {
        title: '二、约束条件',
        content: `本门类配置的硬约束包括：${scenario.constraints.map((c) => `${c.name}${c.buffer_m ? `（缓冲 ${c.buffer_m}m）` : ''}`).join('、')}。其中具备图层数据支撑的约束已参与一票否决，候选地块均已通过该部分校验；缺少对应图层数据的约束未纳入计算，详见第五节数据说明与计算结果说明。`,
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
        content: '本报告数据来源为国土空间规划真实图层数据（研究区：桂林市临桂区），各候选地块的面积与指标得分均由真实空间关系统计计算得出。'
          + '⚠️ 待补充事项：各图层数据的时点（基准年）尚在核实中，补齐前本报告不得用于对外正式发布或作为审批依据。'
          + '正式应用时将对接国土空间规划"一张图"实施监督信息系统。',
      },
    ],
  }
}
