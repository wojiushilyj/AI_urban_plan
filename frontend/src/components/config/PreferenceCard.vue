<script setup lang="ts">
/**
 * 选址偏好设置：5 个统一维度 × 三档（在意/一般/不在意）。
 * 权重由三档偏好自动归一化计算（store/config.ts）。
 * 形态对齐设计稿 .pref-list：每项「图标+名称」一行，其下三档胶囊等宽一行。
 * 传 embedded 时去掉卡片外壳与标题，供 PreferenceTabsCard 页签嵌入。
 */
import { useConfigStore, FACTOR_DEFS, PREFERENCE_LEVELS, type PreferenceLevel } from '../../store/config'
import AppIcon from '../common/AppIcon.vue'

defineProps<{ embedded?: boolean }>()

const config = useConfigStore()

/** 5 个维度对应的图标（与设计稿「选址偏好设置」逐项一致） */
const FACTOR_ICONS: Record<string, string> = {
  urban_planning: 'city',
  transport: 'truck',
  industry: 'network',
  infrastructure: 'civic',
  cost: 'cost',
}

function onLevel(id: string, v: string | number | boolean | undefined): void {
  config.setPreference(id, v as PreferenceLevel)
}
</script>

<template>
  <div class="preference-card" :class="{ 'is-embedded': embedded }">
    <div v-if="!embedded" class="preference-card__title">选址偏好设置</div>
    <div class="preference-card__body">
      <div v-for="f in FACTOR_DEFS" :key="f.id" class="preference-card__row">
        <span class="preference-card__label">
          <AppIcon :name="FACTOR_ICONS[f.id]" :size="14" />
          {{ f.name }}
        </span>
        <el-radio-group
          :model-value="config.preferences[f.id]"
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
  background: var(--bg-panel);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-md);
  overflow: hidden;
}
/* 页签嵌入模式：外壳由 PreferenceTabsCard 提供 */
.preference-card.is-embedded {
  background: none;
  border: none;
  border-radius: 0;
}
.preference-card__title {
  position: relative;
  padding: 10px var(--gap-lg) 10px calc(var(--gap-lg) + 10px);
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.2px;
  border-bottom: 1px solid var(--border-lighter);
}
.preference-card__title::before {
  content: '';
  position: absolute;
  left: var(--gap-lg);
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 14px;
  background: var(--brand);
  border-radius: 2px;
}
/* 维度列表（原型 .pref-list）：纵向排列，行距紧凑 */
.preference-card__body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: var(--gap-sm) var(--gap-lg) var(--gap-md);
}
.preference-card.is-embedded .preference-card__body {
  padding: 0;
}
/* 每项：名称一行 + 档位一行（原型 .pref） */
.preference-card__row {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.preference-card__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
  color: var(--body);
  white-space: nowrap;
}
.preference-card__label :deep(.app-icon) {
  color: var(--muted);
}
</style>
