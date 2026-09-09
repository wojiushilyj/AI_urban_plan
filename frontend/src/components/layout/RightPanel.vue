<script setup lang="ts">
/** 右侧面板（模块 6/7 容器）：结果列表 / 图表分析 / 报告导出 */
import { ref } from 'vue'
import TabPanel from '../common/TabPanel.vue'
import CandidateTable from '../result/CandidateTable.vue'
import RunProgress from '../result/RunProgress.vue'
import ModelSummary from '../result/ModelSummary.vue'
import ChartTabs from '../result/ChartTabs.vue'
import ReportGenerator from '../report/ReportGenerator.vue'
import ScrollPanel from '../common/ScrollPanel.vue'

const active = ref('result')

const tabs = [
  { name: 'result', label: '分析结果', icon: '📊' },
  { name: 'chart', label: '图表分析', icon: '📈' },
  { name: 'report', label: '报告导出', icon: '📄' },
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
.right-panel :deep(.el-tabs) {
  flex: 1;
  overflow: hidden;
}
</style>
