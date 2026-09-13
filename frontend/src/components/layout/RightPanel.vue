<script setup lang="ts">
/** 右侧面板（模块 6/7 容器）：分析结果 / 图表分析 / 报告导出 */
import { computed } from 'vue'
import { useAppStore } from '../../store/app'
import TabPanel from '../common/TabPanel.vue'
import CandidateTable from '../result/CandidateTable.vue'
import RunProgress from '../result/RunProgress.vue'
import ModelSummary from '../result/ModelSummary.vue'
import ChartTabs from '../result/ChartTabs.vue'
import ReportGenerator from '../report/ReportGenerator.vue'
import ScrollPanel from '../common/ScrollPanel.vue'

const app = useAppStore()

/** 右栏页签（v-model 双向绑定到 app.rightTab） */
const active = computed({
  get: () => app.rightTab,
  set: (v: string) => {
    app.rightTab = v
  },
})

const tabs = [
  { name: 'result', label: '分析结果' },
  { name: 'chart', label: '图表分析' },
  { name: 'report', label: '报告导出' },
]
</script>

<template>
  <div class="right-panel">
    <TabPanel v-model:active="active" :tabs="tabs">
      <template #result>
        <ScrollPanel height="100%">
          <RunProgress />
          <ModelSummary />
          <CandidateTable />
        </ScrollPanel>
      </template>
      <template #chart>
        <ScrollPanel height="100%">
          <ChartTabs />
        </ScrollPanel>
      </template>
      <template #report>
        <ScrollPanel height="100%">
          <ReportGenerator />
        </ScrollPanel>
      </template>
    </TabPanel>
  </div>
</template>

<style scoped>
.right-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
