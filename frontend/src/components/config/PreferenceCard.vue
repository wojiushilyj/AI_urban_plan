<script setup lang="ts">
/**
 * 选址偏好设置卡片：5 个统一维度 × 三档（在意/一般/不在意）。
 * 权重由三档偏好自动归一化计算（store/config.ts）。
 */
import { useConfigStore, FACTOR_DEFS, PREFERENCE_LEVELS, type PreferenceLevel } from '../../store/config'

const config = useConfigStore()

function onLevel(id: string, v: string | number | boolean | undefined): void {
  config.setPreference(id, v as PreferenceLevel)
}
</script>

<template>
  <div class="preference-card">
    <div class="preference-card__title">选址偏好设置（影响权重）</div>
    <div class="preference-card__body">
      <div v-for="f in FACTOR_DEFS" :key="f.id" class="preference-card__row">
        <span class="preference-card__label">{{ f.name }}</span>
        <el-radio-group
          :model-value="config.preferences[f.id]"
          size="small"
          @change="(v) => onLevel(f.id, v)"
        >
          <el-radio-button v-for="lv in PREFERENCE_LEVELS" :key="lv.value" :value="lv.value">
            {{ lv.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </div>
  </div>
</template>

<style scoped>
.preference-card {
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  border: 1px solid var(--glass-border-soft);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-glass);
  overflow: hidden;
}
.preference-card__title {
  padding: 10px var(--gap-lg);
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.2px;
  border-bottom: 1px solid var(--border-lighter);
}
.preference-card__body {
  padding: var(--gap-sm) var(--gap-lg) var(--gap-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.preference-card__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-md);
}
.preference-card__label {
  font-size: 14px;
  color: var(--text-regular);
  white-space: nowrap;
}
.preference-card__row :deep(.el-radio-button__inner) {
  padding: 5px 10px;
  font-size: 13px;
}
</style>
