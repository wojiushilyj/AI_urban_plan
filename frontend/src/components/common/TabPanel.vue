<script setup lang="ts">
/** 标签页面板（模块 9.2）：el-tabs 封装 */
defineProps<{
  tabs: { name: string; label: string; icon?: string }[]
}>()
const active = defineModel<string>('active', { required: true })
</script>

<template>
  <el-tabs v-model="active" class="tab-panel">
    <el-tab-pane v-for="t in tabs" :key="t.name" :name="t.name" lazy>
      <template #label>
        <span class="tab-panel__label">
          <span v-if="t.icon">{{ t.icon }}</span>{{ t.label }}
        </span>
      </template>
      <slot :name="t.name" />
    </el-tab-pane>
  </el-tabs>
</template>

<style scoped>
.tab-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.tab-panel :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 var(--gap-sm);
}
.tab-panel :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}
.tab-panel :deep(.el-tab-pane) {
  height: 100%;
}
.tab-panel__label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 15px;
}
/* 选中页签：蓝色背景 + 白色文字（用户要求），圆角只留顶部与下划线呼应 */
.tab-panel :deep(.el-tabs__item.is-active) {
  background: var(--brand, var(--el-color-primary));
  color: #fff;
  border-radius: 8px 8px 0 0;
}
.tab-panel :deep(.el-tabs__item.is-active:hover),
.tab-panel :deep(.el-tabs__item.is-active:focus) {
  color: #fff;
}
</style>
