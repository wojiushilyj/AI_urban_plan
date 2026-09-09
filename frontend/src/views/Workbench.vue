<script setup lang="ts">
/** 工作台：组装顶栏 + 左面板 + 地图 + 右面板 + 状态栏（单页，无路由） */
import { computed } from 'vue'
import { useAppStore } from '../store/app'
import TopNav from '../components/layout/TopNav.vue'
import LeftPanel from '../components/layout/LeftPanel.vue'
import MapStage from '../components/layout/MapStage.vue'
import RightPanel from '../components/layout/RightPanel.vue'
import StatusBar from '../components/common/StatusBar.vue'

const app = useAppStore()
const classes = computed(() => ({ 'workbench--contest': app.contestMode }))
</script>

<template>
  <div class="workbench" :class="classes">
    <TopNav class="workbench__top" />
    <LeftPanel class="workbench__left" />
    <MapStage class="workbench__map" />
    <RightPanel class="workbench__right" />
    <StatusBar class="workbench__status" />
  </div>
</template>
