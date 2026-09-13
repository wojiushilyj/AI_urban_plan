<script setup lang="ts">
/**
 * 选址偏好合并卡片：「选址偏好设置」与「AI 偏好学习」两个页签。
 * 形态对齐设计稿 .seg 胶囊分段（灰底容器 + 等宽胶囊 + 选中黑底白字）。
 * 两张子卡片以 embedded 模式嵌入（去掉各自的卡片外壳与标题）。
 * 用 v-show 保持两个页签挂载，AI 模型数据只加载一次，切换不重新请求。
 */
import { ref } from 'vue'
import PreferenceCard from './PreferenceCard.vue'
import AiModelCard from '../ai/AiModelCard.vue'

const active = ref<'pref' | 'ai'>('pref')
</script>

<template>
  <div class="pref-tabs">
    <div class="seg" role="tablist">
      <button
        type="button"
        class="seg-item"
        :class="{ 'is-active': active === 'pref' }"
        role="tab"
        :aria-selected="active === 'pref'"
        @click="active = 'pref'"
      >
        选址偏好设置
      </button>
      <button
        type="button"
        class="seg-item"
        :class="{ 'is-active': active === 'ai' }"
        role="tab"
        :aria-selected="active === 'ai'"
        @click="active = 'ai'"
      >
        AI 偏好学习
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
  display: flex;
  flex-direction: column;
  gap: 12px;
}
/* 胶囊分段（原型 .seg） */
.seg {
  display: flex;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-pill);
  background: var(--bg-subtle);
}
.seg-item {
  flex: 1 1 0;
  min-width: 0;
  height: 36px;
  border: 0;
  background: transparent;
  border-radius: var(--radius-pill);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 500;
  color: var(--muted);
  cursor: pointer;
  transition: 0.16s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.seg-item:hover {
  color: var(--ink-2);
}
.seg-item.is-active {
  background: var(--ink);
  color: #fff;
  font-weight: 700;
}
/* 固定高度：两个页签内容高度一致，超出部分内部滚动 */
.pref-tabs__pane {
  height: 292px;
  overflow-y: auto;
  overscroll-behavior: contain;
}
</style>
