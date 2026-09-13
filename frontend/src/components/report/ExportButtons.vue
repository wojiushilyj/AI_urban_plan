<script setup lang="ts">
/** 多格式导出按钮组（模块 7.3）：Word / PDF / Excel / 图片 */
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { doExport } from '../../api/export'
import type { ExportFormat } from '../../types/report'
import type { ScenarioDetail } from '../../types/scenario'
import type { SelectionResponse } from '../../types/selection'
import AppIcon from '../common/AppIcon.vue'

const props = defineProps<{
  context: {
    reportHtml?: string
    reportTitle?: string
    scenario?: ScenarioDetail
    result?: SelectionResponse
    weights?: Record<string, number>
    map?: { getCanvas: () => HTMLCanvasElement }
    /** Word 报告数据源（ReportGenerator 组装） */
    docxSource?: unknown
  }
}>()

// icon 为 AppIcon 图标名（Meta 图标体系）
const buttons: { format: ExportFormat; label: string; icon: string; disabled?: boolean }[] = [
  { format: 'docx', label: 'Word 详细报告', icon: 'file-text' },
  { format: 'pdf', label: 'PDF 简版报告', icon: 'file-pdf' },
  { format: 'excel', label: 'Excel 表格', icon: 'file-sheet' },
  { format: 'image', label: '图纸图片', icon: 'image', disabled: !props.context.map },
]

function onExport(format: ExportFormat): void {
  try {
    doExport(format, props.context)
    const label =
      format === 'docx'
        ? 'Word 详细报告'
        : format === 'pdf'
          ? 'PDF 简版报告'
          : format === 'excel'
            ? 'Excel 表格'
            : '图纸图片'
    ElMessage.success(`${label}导出已触发`)
  } catch (e) {
    ElMessage.error(`导出失败：${e instanceof Error ? e.message : String(e)}`)
  }
}

const excelReady = computed(() => Boolean(props.context.scenario && props.context.result && props.context.weights))
const docxReady = computed(() => Boolean(props.context.docxSource))
</script>

<template>
  <div class="export-buttons">
    <el-button v-for="b in buttons" :key="b.format" size="small" :disabled="b.disabled || (b.format === 'excel' && !excelReady) || (b.format === 'docx' && !docxReady)" @click="onExport(b.format)">
      <AppIcon :name="b.icon" :size="14" />
      <span>{{ b.label }}</span>
    </el-button>
  </div>
</template>

<style scoped>
.export-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
  width: 100%;
}
.export-buttons :deep(.el-button) {
  flex: 1 1 auto;
  min-width: 92px;
  margin: 0;
  gap: 6px;
}
</style>
