<script setup lang="ts">
/**
 * 场景切换（模块 1.1）：行业门类下拉，切换后联动约束/权重重载。
 * 形态对齐设计稿 .select：44px 全宽胶囊、灰底无边框、左侧品牌色方片图标。
 */
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useScenarioStore } from '../../store/scenario'
import { useConfigStore } from '../../store/config'
import { useResultStore } from '../../store/result'
import { useMapStore } from '../../store/map'
import AppIcon from '../common/AppIcon.vue'

const scenario = useScenarioStore()
const config = useConfigStore()
const result = useResultStore()
const map = useMapStore()

onMounted(async () => {
  await scenario.fetchList()
  const detail = await scenario.switchScenario('B')
  config.applyScenario(detail)
})

async function onSwitch(id: string): Promise<void> {
  const detail = await scenario.switchScenario(id)
  config.applyScenario(detail)
  result.reset()
  map.selectedRank = null
  ElMessage.success(`已切换到「${detail.name}」，约束与权重已重载`)
}
</script>

<template>
  <el-select
    :model-value="scenario.currentId"
    placeholder="选择行业门类"
    class="scenario-switcher"
    popper-class="scenario-switcher__popper"
    @change="onSwitch"
  >
    <el-option v-for="s in scenario.list" :key="s.id" :value="s.id" :label="s.name">
      <div class="scenario-option">
        <span class="scenario-option__id">{{ s.id }}</span>
        <span>{{ s.name }}</span>
        <span class="scenario-option__category">{{ s.category }}</span>
      </div>
    </el-option>
    <template #label>
      <span class="scenario-switcher__label">
        <AppIcon name="grid" :size="22" />
        <span class="scenario-switcher__text">{{ scenario.current?.name ?? '选择行业门类' }}</span>
      </span>
    </template>
  </el-select>
</template>

<style scoped>
.scenario-switcher {
  width: 100%;
}
.scenario-switcher__label {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.scenario-switcher__text {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.scenario-option {
  display: flex;
  align-items: center;
  gap: 8px;
}
.scenario-option__id {
  font-size: 13px;
  font-weight: 700;
  color: var(--brand);
  background: var(--brand-light-9);
  border-radius: 4px;
  padding: 0 5px;
}
.scenario-option__category {
  margin-left: auto;
  font-size: 13px;
  color: var(--text-secondary);
}
</style>

<style>
/* 下拉触发器：对齐原型 .select（44px 胶囊 / 灰底 / 无边框） */
.scenario-switcher .el-select__wrapper {
  min-height: 44px;
  padding: 0 12px 0 16px;
  border-radius: var(--radius-pill);
  background: var(--bg-subtle);
  box-shadow: none !important;
  transition: background 0.16s ease;
}
.scenario-switcher .el-select__wrapper:hover,
.scenario-switcher .el-select__wrapper.is-focused {
  background: var(--border-light);
  box-shadow: none !important;
}
/* 弹层选项左对齐，避免居中偏移 */
.scenario-switcher__popper .el-select-dropdown__item {
  justify-content: flex-start;
}
</style>
