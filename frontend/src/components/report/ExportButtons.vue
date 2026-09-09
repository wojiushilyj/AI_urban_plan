<script setup lang="ts">
/** 多格式导出按钮组（模块 7.3）：PDF / Excel / 图片 */
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { doExport } from '../../api/export'
import type { ExportFormat } from '../../types/report'
import type { ScenarioDetail } from '../../types/scenario'
import type { SelectionResponse } from '../../types/selection'

const props = defineProps<{
  context: {
    reportHtml?: string
    reportTitle?: string
    scenario?: ScenarioDetail
    result?: SelectionResponse
    weights?: Record<string, number>
    map?: { getCanvas: () => HTMLCanvasElement }
  }
}>()

const buttons: { format: ExportFormat; label: string; icon: string; disabled?: boolean }[] = [
  { format: 'pdf', label: 'PDF 报告', icon: '📕' },
  { format: 'excel', label: 'Excel 表格', icon: '📊' },
  { format: 'image', label: '图纸图片', icon: '🖼️', disabled: !props.context.map },
]

function onExport(format: ExportFormat): void {
  try {
    doExport(format, props.context)
    const label = format === 'pdf' ? 'PDF 报告' : format === 'excel' ? 'Excel 表格' : '图纸图片'
    ElMessage.success(`${label}导出已触发（样例数据）`)
  } catch (e) {
    ElMessage.error(`导出失败：${e instanceof Error ? e.message : String(e)}`)
  }
}

const excelReady = computed(() => Boolean(props.context.scenario && props.context.result && props.context.weights))
</script>

<template>
  <div class="export-buttons">
    <el-button v-for="b in buttons" :key="b.format" size="small" :disabled="b.disabled || (b.format === 'excel' && !excelReady)" @click="onExport(b.format)">
      {{ b.icon }} {{ b.label }}
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
}
</style>
