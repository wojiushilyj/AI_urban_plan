<script setup lang="ts">
/**
 * 底部状态栏（对齐设计稿 .statusbar）：39px 高、11.5px 字号。
 * 左侧：绿点 + 数据源（主色加粗）+ `·` 分隔的键值对；右侧：脉冲点 + 状态。
 */
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
    <div class="status-bar__left">
      <i class="dot-sm" />
      <span class="status-bar__key">真实规划数据</span>
      <span class="status-bar__sep">·</span>
      <span class="status-bar__val">门类：{{ scenario.current?.name ?? '—' }}</span>
      <span class="status-bar__sep">·</span>
      <span class="status-bar__val">研究区：{{ aoiArea }}</span>
      <span class="status-bar__sep">·</span>
      <span class="status-bar__val">候选地块：{{ result.response?.candidates.length ?? 0 }}</span>
      <span class="status-bar__sep">·</span>
      <span class="status-bar__val">坐标系：CGCS2000 / 3° 带</span>
      <span v-if="result.running" class="status-bar__progress">
        <el-progress
          :percentage="result.percent"
          :stroke-width="4"
          :show-text="false"
          style="width: 110px"
        />
      </span>
    </div>

    <div class="status-bar__right">
      <i class="pulse" />
      {{ app.statusMessage }}
    </div>
  </footer>
</template>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: var(--statusbar-height);
  padding: 0 24px;
  background: #FFFFFF;
  border-top: 1px solid var(--border-lighter);
}
.status-bar__left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11.5px;
  min-width: 0;
  overflow: hidden;
}
.status-bar__key {
  font-weight: 700;
  color: var(--body);
  white-space: nowrap;
}
.status-bar__val {
  color: var(--muted);
  white-space: nowrap;
}
.status-bar__sep {
  color: var(--border-strong);
}
.status-bar__progress {
  display: inline-flex;
  align-items: center;
  margin-left: 2px;
}
.status-bar__right {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 700;
  color: var(--c-success);
  white-space: nowrap;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dot-sm {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-success);
  flex: 0 0 6px;
}
/* 脉冲点（原型 .pulse） */
.pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--c-success);
  position: relative;
  flex: 0 0 7px;
}
.pulse::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background: var(--c-success);
  opacity: 0.35;
  animation: pulse 1.8s ease-out infinite;
}
@keyframes pulse {
  0% { transform: scale(0.7); opacity: 0.45; }
  70% { transform: scale(1.6); opacity: 0; }
  100% { opacity: 0; }
}
</style>
