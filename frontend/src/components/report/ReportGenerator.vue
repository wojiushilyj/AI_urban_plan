<script setup lang="ts">
/**
 * 报告生成与导出（模块 7）：自动文本生成 + 预览 + 多格式导出。
 */
import { computed, ref } from 'vue'
import { useResultStore } from '../../store/result'
import { useScenarioStore } from '../../store/scenario'
import { useConfigStore, ALGORITHM_OPTIONS } from '../../store/config'
import { useMapStore } from '../../store/map'
import { mockGenerateReport } from '../../mock/report'
import type { ReportDoc } from '../../types/report'
import CardContainer from '../common/CardContainer.vue'
import ReportPreview from './ReportPreview.vue'
import ExportButtons from './ExportButtons.vue'

const result = useResultStore()
const scenario = useScenarioStore()
const config = useConfigStore()
const map = useMapStore()

const report = ref<ReportDoc | null>(null)

const algoName = computed(
  () => ALGORITHM_OPTIONS.find((a) => a.id === config.algorithm)?.name ?? '—'
)

function generate(): void {
  if (!scenario.detail || !result.response) return
  report.value = mockGenerateReport(scenario.detail, result.response, {
    grid_size_m: config.gridSize,
    top_n: config.topN,
    algorithm: algoName.value,
  })
}

/** 报告 HTML（预览 + PDF 打印共用） */
const reportHtml = computed(() => {
  if (!report.value) return ''
  return report.value.sections
    .map((s) => `<h2>${s.title}</h2><p>${s.content.replace(/\n/g, '<br/>')}</p>`)
    .join('')
})

/** 导出上下文 */
const exportContext = computed(() => ({
  reportHtml: reportHtml.value,
  reportTitle: report.value?.title ?? '选址报告',
  scenario: scenario.detail ?? undefined,
  result: result.response ?? undefined,
  weights: config.weights,
  map: map.mapInstance ?? undefined,
}))
</script>

<template>
  <div class="report-generator">
    <CardContainer title="选址报告" :subtitle="'基于当前结果自动生成，含样例数据标注'">
      <div class="report-generator__toolbar">
        <el-button type="primary" :disabled="!result.response" @click="generate">
          {{ report ? '重新生成报告' : '生成报告' }}
        </el-button>
        <ExportButtons v-if="report" :context="exportContext" />
      </div>
      <el-empty
        v-if="!result.response"
        description="先完成选址计算，再生成报告"
        :image-size="70"
      />
      <ReportPreview v-else-if="report" :report="report" />
      <div v-else class="report-generator__placeholder">
        点击「生成报告」基于当前 Top-{{ config.topN }} 候选结果生成
      </div>
    </CardContainer>
  </div>
</template>

<style scoped>
.report-generator {
  padding: var(--gap-md);
}
.report-generator__toolbar {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  margin-bottom: var(--gap-md);
}
.report-generator__placeholder {
  padding: var(--gap-lg);
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}
</style>
