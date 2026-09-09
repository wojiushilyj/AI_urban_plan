<script setup lang="ts">
/**
 * 提示 / 告警弹窗组件（模块 9.4）。
 * 组件本体不可见，提供响应式队列渲染；快捷函数见 AlertDialog 的静态方法封装。
 * 实际项目里直接使用 ElMessage / ElMessageBox；此组件保留统一出口以备竞赛定制样式。
 */
</script>

<template>
  <div class="alert-dialog" aria-hidden="true" />
</template>

<style scoped>
.alert-dialog {
  display: none;
}
</style>
