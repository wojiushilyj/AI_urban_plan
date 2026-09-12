<script setup lang="ts">
/**
 * 选址偏好合并卡片：「选址偏好」与「AI 偏好学习（机器学习徽标）」两个页签。
 * 两张子卡片以 embedded 模式嵌入（去掉各自的卡片外壳与标题），点击页签切换。
 * 用 v-show 保持两个页签挂载，AI 模型数据只加载一次，切换不重新请求。
 */
import { ref } from 'vue'
import PreferenceCard from './PreferenceCard.vue'
import AiModelCard from '../ai/AiModelCard.vue'

const active = ref<'pref' | 'ai'>('pref')
</script>

<template>
  <div class="pref-tabs">
    <div class="pref-tabs__header" role="tablist">
      <button
        type="button"
        class="pref-tabs__tab"
        :class="{ 'is-active': active === 'pref' }"
        role="tab"
        :aria-selected="active === 'pref'"
        @click="active = 'pref'"
      >
        <span class="pref-tabs__label">选址偏好</span>
      </button>
      <button
        type="button"
        class="pref-tabs__tab"
        :class="{ 'is-active': active === 'ai' }"
        role="tab"
        :aria-selected="active === 'ai'"
        @click="active = 'ai'"
      >
        <span class="pref-tabs__label pref-tabs__label--ai">AI 偏好学习</span>
        <span class="pref-tabs__badge">机器学习</span>
      </button>
    </div>

    <div v-show="active === 'pref'" class="pref-tabs__pane" role="tabpanel">
      <PreferenceCard embedded />
    </div>
    <div v-show="active === 'ai'" class="pref-tabs__pane" role="tabpanel">
      <AiModelCard embedded />
    </div>
  </div>
</template>

<style scoped>
.pref-tabs {
  background: var(--glass-bg);
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  border: 1px solid var(--glass-border-soft);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-glass);
  overflow: hidden;
}
.pref-tabs__header {
  display: flex;
  border-bottom: 1px solid var(--border-lighter);
  background: rgba(124, 92, 230, 0.04);
}
.pref-tabs__tab {
  position: relative;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  letter-spacing: 0.2px;
  white-space: nowrap;
  transition: color var(--duration-base) var(--ease-in-out);
}
.pref-tabs__tab:hover {
  color: var(--text-primary);
}
/* 页签文字前的竖线装饰，与全项目卡片标题样式一致（3px 圆角短竖条） */
.pref-tabs__label {
  position: relative;
  padding-left: 9px;
}
.pref-tabs__label::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 12px;
  background: var(--brand, var(--el-color-primary));
  border-radius: 2px;
}
.pref-tabs__label--ai::before {
  background: #7C5CE6;
}
.pref-tabs__badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 500;
  color: #7C5CE6;
  background: rgba(124, 92, 230, 0.1);
  border: 1px solid rgba(124, 92, 230, 0.25);
  border-radius: 999px;
  padding: 0 6px;
  line-height: 16px;
}
.pref-tabs__tab.is-active {
  color: var(--text-primary);
}
.pref-tabs__tab.is-active::after {
  content: '';
  position: absolute;
  left: 20%;
  right: 20%;
  bottom: -1px;
  height: 2px;
  background: var(--brand, var(--el-color-primary));
  border-radius: 2px 2px 0 0;
}
.pref-tabs__pane {
  /* 固定高度：两个页签卡片高度一致，超出部分内部滚动（滚动条样式复用全局 ::-webkit-scrollbar） */
  height: 300px;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: var(--gap-sm) var(--gap-lg) var(--gap-md);
}
</style>
