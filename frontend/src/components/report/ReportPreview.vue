<script setup lang="ts">
/** 报告预览（模块 7.2） */
import type { ReportDoc } from '../../types/report'

defineProps<{ report: ReportDoc }>()
</script>

<template>
  <div class="report-preview">
    <div class="report-preview__head">
      <h1>{{ report.title }}</h1>
      <p class="report-preview__meta">生成时间：{{ report.generatedAt }} · 样例数据</p>
    </div>
    <div v-for="(s, i) in report.sections" :key="i" class="report-preview__section">
      <h2>{{ s.title }}</h2>
      <p>{{ s.content }}</p>
    </div>
    <div class="report-preview__watermark">SAMPLE · 演示样例数据</div>
  </div>
</template>

<style scoped>
.report-preview {
  background: #fff;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: var(--gap-lg);
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-regular);
  max-height: 420px;
  overflow-y: auto;
}
.report-preview__head {
  text-align: center;
  margin-bottom: var(--gap-md);
}
.report-preview__head h1 {
  font-size: 19px;
  color: var(--text-primary);
}
.report-preview__meta {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.report-preview__section h2 {
  font-size: 15px;
  color: var(--brand-dark-2);
  margin: 12px 0 4px;
}
.report-preview__section p {
  white-space: pre-wrap;
}
.report-preview__watermark {
  margin-top: var(--gap-md);
  text-align: center;
  font-size: 12px;
  color: var(--c-danger);
  letter-spacing: 1px;
}
</style>
