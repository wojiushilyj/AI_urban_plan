/**
 * 导出接口（模块 8.4）：PDF / Excel / 图片，全部前端本地生成。
 * 不引入重型导出库：PDF 走浏览器打印、Excel 用 Blob(ms-excel)、图片用 canvas 截图。
 */
import type { ScenarioDetail } from '../types/scenario'
import type { SelectionResponse } from '../types/selection'

export type { ExportFormat } from '../types/report'
import type { ExportFormat } from '../types/report'

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

/** 导出报告 PDF：打开打印窗口（浏览器"另存为 PDF"） */
export function exportPdf(reportHtml: string, title: string): void {
  const w = window.open('', '_blank', 'width=900,height=700')
  if (!w) {
    window.alert('浏览器拦截了弹出窗口，请允许弹窗后重试')
    return
  }
  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title>
<style>
  body { font-family: 'PingFang SC','Microsoft YaHei',serif; margin: 48px; color: #1F2937; line-height: 1.8; }
  h1 { font-size: 24px; text-align: center; margin-bottom: 4px; }
  .meta { text-align: center; color: #9CA3AF; font-size: 14px; margin-bottom: 32px; }
  h2 { font-size: 18px; margin: 24px 0 8px; color: #3B82F6; }
  .watermark { position: fixed; bottom: 24px; left: 0; right: 0; text-align: center; color: #9CA3AF; font-size: 13px; }
  @media print { .watermark { position: static; } }
</style></head><body>${reportHtml}
<div class="watermark">数据来源：国土空间规划真实图层数据</div>
</body></html>`)
  w.document.close()
  setTimeout(() => w.print(), 300)
}

/** 导出 Excel（权重 + 候选地块表，Blob CSV 兼容 ms-excel） */
export function exportExcel(
  scenario: ScenarioDetail,
  result: SelectionResponse,
  weights: Record<string, number>
): void {
  const esc = (v: unknown) => `"${String(v).replace(/"/g, '""')}"`
  const lines: string[] = []
  lines.push(`${scenario.name}选址分析结果`)
  lines.push('')
  lines.push('[权重配置]')
  lines.push('指标,权重')
  for (const [k, v] of Object.entries(weights)) {
    lines.push(`${esc(k)},${v}`)
  }
  lines.push('')
  lines.push('[候选地块]')
  lines.push('排名,综合得分,面积(公顷),' + scenario.factors.map((f) => esc(f.name)).join(','))
  for (const c of result.candidates) {
    lines.push([c.rank, c.score, c.area_ha, ...scenario.factors.map((f) => c.factors[f.id] ?? '')].join(','))
  }
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'application/ms-excel;charset=utf-8' })
  downloadBlob(blob, `选址结果_${scenario.id}_${new Date().toISOString().slice(0, 10)}.xls`)
}

/** 导出图纸图片：传入 MapLibre map 实例，preserveDrawingBuffer 需开启 */
export function exportImage(map: { getCanvas: () => HTMLCanvasElement }, filename: string): void {
  const canvas = map.getCanvas()
  const url = canvas.toDataURL('image/png')
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
}

/** 统一导出入口 */
export function doExport(format: ExportFormat, ctx: {
  reportHtml?: string
  reportTitle?: string
  scenario?: ScenarioDetail
  result?: SelectionResponse
  weights?: Record<string, number>
  map?: { getCanvas: () => HTMLCanvasElement }
  /** Word 报告附加数据源（见 reportDocx.ts ReportDocxSource） */
  docxSource?: unknown
}): void {
  if (format === 'docx' && ctx.docxSource) {
    // 动态加载 docx 生成模块：库体积较大，按需分包，不拖累首屏
    void import('./reportDocx').then(({ exportReportDocx }) => exportReportDocx(ctx.docxSource as never))
  } else if (format === 'pdf' && ctx.reportHtml) {
    exportPdf(ctx.reportHtml, ctx.reportTitle ?? '选址报告')
  } else if (format === 'excel' && ctx.scenario && ctx.result && ctx.weights) {
    exportExcel(ctx.scenario, ctx.result, ctx.weights)
  } else if (format === 'image' && ctx.map) {
    exportImage(ctx.map, `选址图纸_${new Date().toISOString().slice(0, 10)}.png`)
  }
}
