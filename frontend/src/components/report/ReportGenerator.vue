<script setup lang="ts">
/**
 * 报告生成与导出（模块 7）：自动文本生成 + 预览 + 多格式导出。
 */
import { computed, ref } from 'vue'
import { useResultStore } from '../../store/result'
import { useScenarioStore } from '../../store/scenario'
import { useConfigStore, ALGORITHM_OPTIONS } from '../../store/config'
import { useAiStore } from '../../store/ai'
import { useMapStore } from '../../store/map'
import { mockGenerateReport } from '../../mock/report'
import type { ReportDoc } from '../../types/report'
import CardContainer from '../common/CardContainer.vue'
import ReportPreview from './ReportPreview.vue'
import ExportButtons from './ExportButtons.vue'

const result = useResultStore()
const scenario = useScenarioStore()
const config = useConfigStore()
const ai = useAiStore()
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
  weights: result.response?.weights ?? config.weights,
  map: map.mapInstance ?? undefined,
  /** Word 报告数据源：按用户模板结构组装（reportDocx.ts） */
  docxSource:
    scenario.detail && result.response
      ? {
          scenario: scenario.detail,
          result: result.response,
          weights: result.response.weights ?? config.weights,
          preferences: config.preferences,
          parseResult: ai.parseResult,
          config: {
            algorithmName: algoName.value,
            gridSize: config.gridSize,
            topN: config.topN,
            minAreaHa: config.minAreaHa,
            targetAreaHa: config.targetAreaHa,
            areaRange: config.areaRange,
            weightModeName:
              config.weightMode === 'expert'
                ? '专家权重（AHP+熵权）'
                : config.weightMode === 'learned'
                  ? 'AI 学习权重'
                  : '专家 + AI 混合权重',
            weightSource: result.response.weight_source,
          },
          map: map.mapInstance ?? undefined,
        }
      : undefined,
}))
</script>

<template>
  <div class="report-generator">
    <CardContainer title="选址报告" subtitle="基于当前结果自动生成">
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
      <template v-else-if="report">
        <div class="report-generator__notice">
          以下页面内容为<b>简版报告</b>（纯文字速览）。完整封面、目录、图表与表格排版请点击「Word 详细报告」导出；如需打印当前预览，可导出「PDF 简版报告」。
        </div>
        <ReportPreview :report="report" />
      </template>
      <div v-else class="report-generator__placeholder">
        点击「生成报告」基于当前 Top-{{ config.topN }} 候选结果生成
      </div>
    </CardContainer>
  </div>
</template>

<style scoped>
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
.report-generator__notice {
  margin-bottom: var(--gap-md);
  padding: 10px 14px;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 13px;
  line-height: 1.6;
}
</style>
