/**
 * 导出 composable（模块 7.3）：PDF / Excel / 图片。
 * 薄封装 api/export，负责拼接上下文与成功提示。
 */
import { ElMessage } from 'element-plus'
import { doExport, type ExportFormat } from '../api/export'

export function useExport(getContext: () => Parameters<typeof doExport>[1]) {
  async function exportAs(format: ExportFormat): Promise<void> {
    try {
      doExport(format, getContext())
      const label = format === 'pdf' ? 'PDF 报告' : format === 'excel' ? 'Excel 表格' : '图纸图片'
      ElMessage.success(`${label}导出已触发（样例数据）`)
    } catch (e) {
      ElMessage.error(`导出失败：${e instanceof Error ? e.message : String(e)}`)
    }
  }

  return { exportAs }
}
