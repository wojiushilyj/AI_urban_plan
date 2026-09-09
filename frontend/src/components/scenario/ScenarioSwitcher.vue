<script setup lang="ts">
/** 场景切换（模块 1.1）：行业门类下拉，切换后联动约束/权重重载 */
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useScenarioStore } from '../../store/scenario'
import { useConfigStore } from '../../store/config'
import { useResultStore } from '../../store/result'
import { useMapStore } from '../../store/map'

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
    style="width: 260px"
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
        <span class="scenario-option__id">{{ scenario.currentId }}</span>
        {{ scenario.current?.name ?? '选择行业门类' }}
      </span>
    </template>
  </el-select>
</template>

<style scoped>
.scenario-switcher__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
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
