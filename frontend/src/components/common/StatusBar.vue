<script setup lang="ts">
/** 底部状态栏（模块 1.2 / 9）：连接状态、场景、研究区、进度 */
import { computed } from 'vue'
import { useAppStore } from '../../store/app'
import { useScenarioStore } from '../../store/scenario'
import { useResultStore } from '../../store/result'

const app = useAppStore()
const scenario = useScenarioStore()
const result = useResultStore()

const aoiArea = computed(() => '临桂区')
</script>

<template>
  <footer class="status-bar">
    <span class="status-bar__item">
      <span class="dot" :class="app.backendMode === 'mock' ? 'dot--warn' : 'dot--ok'" />
      {{ app.backendMode === 'mock' ? '样例数据模式' : '已连接后端' }}
    </span>
    <span class="status-bar__divider" />
    <span class="status-bar__item">门类：{{ scenario.current?.name ?? '—' }}</span>
    <span class="status-bar__divider" />
    <span class="status-bar__item">研究区：{{ aoiArea }}</span>
    <span class="status-bar__divider" />
    <span class="status-bar__item">候选地块：{{ result.response?.candidates.length ?? 0 }} 个</span>
    <span v-if="result.running" class="status-bar__progress">
      <el-progress
        :percentage="result.percent"
        :stroke-width="4"
        :show-text="false"
        style="width: 120px"
      />
    </span>
    <span class="status-bar__spacer" />
    <span class="status-bar__item status-bar__msg">{{ app.statusMessage }}</span>
    <span class="status-bar__tag">SAMPLE · 演示样例数据</span>
  </footer>
</template>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  height: var(--statusbar-height);
  padding: 0 var(--gap-lg);
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  border-top: 1px solid var(--glass-border-soft);
  box-shadow: var(--shadow-glass);
  font-size: 14px;
  color: var(--text-secondary);
}
.status-bar__item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.status-bar__msg {
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.status-bar__divider {
  width: 1px;
  height: 10px;
  background: var(--border-light);
}
.status-bar__spacer {
  flex: 1;
}
.status-bar__tag {
  color: var(--c-warning);
  font-weight: 600;
  letter-spacing: 0.4px;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}
.dot--ok {
  background: var(--c-success);
}
.dot--warn {
  background: var(--c-warning);
}
</style>
