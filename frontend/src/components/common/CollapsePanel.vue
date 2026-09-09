<script setup lang="ts">
/** 折叠面板（模块 9.5）：el-collapse 封装 */
defineProps<{
  titles: string[]
  defaultOpen?: string[]
}>()
const open = defineModel<string[]>('open', { default: () => [] })
</script>

<template>
  <el-collapse v-model="open" class="collapse-panel">
    <el-collapse-item v-for="(t, i) in titles" :key="i" :title="t" :name="String(i)">
      <slot :name="`panel-${i}`" :index="i" />
    </el-collapse-item>
  </el-collapse>
</template>

<style scoped>
.collapse-panel :deep(.el-collapse-item__header) {
  font-size: 15px;
  font-weight: 500;
}
.collapse-panel :deep(.el-collapse-item__content) {
  padding-bottom: 8px;
}
</style>
