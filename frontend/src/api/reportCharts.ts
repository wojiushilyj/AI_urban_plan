/**
 * 报告图表离屏渲染（供 Word 报告嵌入）：
 * 用 ECharts 无头渲染为 PNG dataURL，不依赖页面中已挂载的图表实例。
 */
import * as echarts from 'echarts'
import type { ScenarioDetail } from '../types/scenario'
import type { SelectionResponse } from '../types/selection'
import { FACTOR_DEFS } from '../store/config'

/** 离屏渲染一张 ECharts 图为 PNG dataURL（pixelRatio 2 保证打印清晰度） */
export function renderChartPng(
  option: echarts.EChartsCoreOption,
  width = 620,
  height = 320
): string {
  const div = document.createElement('div')
  div.style.cssText = `position:fixed;left:-9999px;top:0;width:${width}px;height:${height}px;background:#fff;`
  document.body.appendChild(div)
  const chart = echarts.init(div, undefined, { width, height })
  try {
    // ⚠️ 必须关闭动画：否则 getDataURL 捕获的是动画第 0 帧（仅坐标轴框架、无数据系列）
    chart.setOption({ animation: false, ...option } as echarts.EChartsCoreOption)
    return chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' })
  } finally {
    chart.dispose()
    div.remove()
  }
}

/** 图 1：本次权重总览（饼图） */
export function weightsPiePng(weights: Record<string, number>): string {
  const data = FACTOR_DEFS.map((f) => ({
    name: f.name,
    value: Math.round((weights[f.id] ?? 0) * 1000) / 10,
  }))
  return renderChartPng(
    {
      tooltip: { trigger: 'item', formatter: '{b}：{c}%' },
      legend: { bottom: 0, fontSize: 12 },
      series: [
        {
          type: 'pie',
          radius: ['38%', '62%'],
          center: ['50%', '44%'],
          label: { formatter: '{b} {c}%', fontSize: 11 },
          data,
          color: ['#3B82F6', '#F59E0B', '#10B981', '#8B5CF6', '#EF4444'],
        },
      ],
    },
    620,
    300
  )
}

/** 图 2：候选地块综合得分（柱状图） */
export function candidateScoreBarPng(result: SelectionResponse): string {
  const labels = result.candidates.map(
    (c) => c.code ?? `地块${c.rank}`
  )
  const scores = result.candidates.map((c) => Number(c.score.toFixed ? c.score.toFixed(4) : c.score))
  return renderChartPng(
    {
      grid: { left: 56, right: 24, top: 36, bottom: 56 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11, interval: 0 } },
      yAxis: { type: 'value', name: '综合得分', axisLabel: { fontSize: 11 } },
      series: [
        {
          type: 'bar',
          data: scores.map((v, i) => ({
            value: v,
            itemStyle: { color: i === 0 ? '#3B82F6' : '#93C5FD' },
          })),
          barMaxWidth: 42,
          label: { show: true, position: 'top', fontSize: 10, formatter: (p: { value: number }) => String(p.value) },
        },
      ],
    },
    620,
    300
  )
}

/** 图 3：Top-3 候选地块五维雷达图 */
export function topRadarPng(scenario: ScenarioDetail, result: SelectionResponse): string {
  const indicators = scenario.factors.map((f) => ({ name: f.name, max: 100 }))
  const top3 = result.candidates.slice(0, 3)
  return renderChartPng(
    {
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, fontSize: 12 },
      radar: {
        indicator: indicators,
        radius: '60%',
        center: ['50%', '48%'],
        axisName: { fontSize: 12, color: '#6B7280' },
        splitArea: { areaStyle: { color: ['#FFFFFF', '#F9FAFB'] } },
      },
      series: [
        {
          type: 'radar',
          data: top3.map((c, i) => ({
            name: `No.${c.rank} ${c.code ?? ''}`.trim(),
            // 因子分本身为 0–100 分制（后端引擎口径），直接使用；误乘 100 会超出雷达 max=100，
            // 多边形顶点飞出画布 → 画布被末位系列半透明填充整体染色、数据不可见
            value: scenario.factors.map((f) => Math.round(c.factors[f.id] ?? 0)),
            areaStyle: { opacity: 0.15 },
            lineStyle: { width: 2 },
            itemStyle: { color: ['#3B82F6', '#F59E0B', '#EF4444'][i % 3] },
          })),
        },
      ],
    },
    560,
    380
  )
}

/** 图 4：地图快照（当前视口），失败返回 null（报告自动跳过该图） */
export function mapSnapshotPng(map: { getCanvas: () => HTMLCanvasElement }): string | null {
  try {
    return map.getCanvas().toDataURL('image/png')
  } catch {
    return null
  }
}

/** dataURL → Uint8Array（docx ImageRun 入参） */
export function dataUrlToU8(url: string): Uint8Array {
  const b64 = url.slice(url.indexOf(',') + 1)
  const bin = atob(b64)
  const u8 = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i += 1) u8[i] = bin.charCodeAt(i)
  return u8
}
