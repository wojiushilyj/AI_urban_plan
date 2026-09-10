<script setup lang="ts">
/**
 * 图层要素信息卡片（工具条「要素查询」模式）：
 * 单击地图上的图层要素后，在点击位置附近弹出，展示图层名、几何类型、
 * 几何量测值（面→面积 / 线→长度）与要素的全部业务属性字段。
 *
 * 定位：卡片挂在 .map-stage（position:relative）内，用绝对定位跟随点击点；
 * 靠近容器右下边界时自动翻到点击点另一侧，并夹紧在容器内。
 */
import { computed, nextTick, ref, watch } from 'vue'
import type { FeaturePick } from '../../store/map'
import { placeCard } from '../../utils/overlay'
import { toFieldRows } from '../../utils/featureProps'

const props = defineProps<{ pick: FeaturePick | null }>()
const emit = defineEmits<{ close: [] }>()

/** 卡片宽度（像素，与样式中的 width 保持一致） */
const CARD_W = 332

const root = ref<HTMLElement>()
/** 卡片位置；初值放到容器外，避免首帧在左上角闪一下 */
const pos = ref({ left: -9999, top: -9999 })

/** 属性 → 展示行（纯函数，见 utils/featureProps.ts） */
const rows = computed(() => toFieldRows(props.pick?.properties))

/** 定位：默认落在点击点右下方，越界则翻到另一侧并夹紧（见 utils/overlay.ts） */
async function place(): Promise<void> {
  const p = props.pick
  if (!p) return
  await nextTick()
  const el = root.value
  if (!el) return
  // offsetParent 即 .map-stage（position:relative），与 MapLibre 的 e.point 同一坐标系
  const parent = el.offsetParent as HTMLElement | null
  pos.value = placeCard({
    anchor: p.screen,
    cardWidth: CARD_W,
    cardHeight: el.offsetHeight,
    containerWidth: parent?.clientWidth ?? el.clientWidth,
    containerHeight: parent?.clientHeight ?? el.clientHeight,
  })
}

watch(() => props.pick, place, { immediate: true })
</script>

<template>
  <transition name="feature-card">
    <aside
      v-if="pick"
      ref="root"
      class="feature-info-card"
      :style="{ left: `${pos.left}px`, top: `${pos.top}px`, width: `${CARD_W}px` }"
    >
      <header class="feature-info-card__head">
        <span class="feature-info-card__title">{{ pick.layerName }}</span>
        <el-button class="feature-info-card__close" text @click="emit('close')">✕</el-button>
      </header>

      <div class="feature-info-card__meta">
        <el-tag size="small" effect="plain" type="info">{{ pick.geomLabel }}</el-tag>
        <span v-if="pick.measure" class="feature-info-card__measure">{{ pick.measure }}</span>
      </div>

      <div v-if="rows.length" class="feature-info-card__rows">
        <template v-for="r in rows" :key="r.key">
          <!-- 长文本（如园区介绍）整段排版 -->
          <div v-if="r.long" class="feature-info-card__block">
            <span class="feature-info-card__block-label">{{ r.label }}</span>
            <p class="feature-info-card__block-value">{{ r.value }}<em v-if="r.unit">{{ r.unit }}</em></p>
          </div>
          <!-- 短字段维持「标签 | 值」两栏 -->
          <div v-else class="feature-info-card__row">
            <span class="feature-info-card__label">{{ r.label }}</span>
            <span class="feature-info-card__value">
              {{ r.value }}<em v-if="r.unit">{{ r.unit }}</em>
            </span>
          </div>
        </template>
      </div>
      <p v-else class="feature-info-card__empty">该要素未携带业务属性字段</p>

      <p class="feature-info-card__coord">拾取位置 {{ pick.lngLat }}</p>
    </aside>
  </transition>
</template>

<style scoped>
.feature-info-card {
  position: absolute;
  z-index: 22;
  max-height: calc(100% - 24px);
  display: flex;
  flex-direction: column;
  padding: var(--gap-md) var(--gap-lg);
  background: var(--bg-panel);
  border: 1px solid var(--border-lighter);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
}
.feature-info-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  padding-bottom: var(--gap-sm);
  border-bottom: 1px solid var(--border-lighter);
  flex-shrink: 0;
}
.feature-info-card__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-regular);
  letter-spacing: 0.3px;
}
.feature-info-card__close {
  flex-shrink: 0;
  font-size: 16px;
  color: var(--text-secondary);
  padding: 2px 4px;
}
.feature-info-card__meta {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: var(--gap-sm) 0;
  flex-shrink: 0;
}
.feature-info-card__measure {
  font-size: 14px;
  font-weight: 600;
  color: var(--brand-dark-2);
}
.feature-info-card__rows {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
  padding-bottom: var(--gap-sm);
  border-bottom: 1px solid var(--border-lighter);
  overflow-y: auto;
  /* flex 子项默认 min-height:auto 会撑破卡片，导致内容被裁掉而非滚动 */
  min-height: 0;
}
.feature-info-card__row {
  display: flex;
  gap: var(--gap-sm);
  font-size: 14px;
}
.feature-info-card__label {
  flex-shrink: 0;
  width: 76px;
  color: var(--text-secondary);
}
.feature-info-card__value {
  flex: 1;
  min-width: 0;
  color: var(--text-regular);
  word-break: break-all;
}
.feature-info-card__value em {
  font-style: normal;
  font-size: 12px;
  color: var(--text-secondary);
  margin-left: 2px;
}
/* 长文本字段：标签一行、正文整段占满宽度 */
.feature-info-card__block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.feature-info-card__block-label {
  font-size: 12px;
  color: var(--text-secondary);
  letter-spacing: 0.3px;
}
.feature-info-card__block-value {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-regular);
  white-space: pre-wrap;
  word-break: break-word;
}
.feature-info-card__block-value em {
  font-style: normal;
  font-size: 12px;
  color: var(--text-secondary);
  margin-left: 2px;
}
.feature-info-card__empty {
  margin: 0;
  padding-bottom: var(--gap-sm);
  border-bottom: 1px solid var(--border-lighter);
  font-size: 14px;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.feature-info-card__coord {
  margin: 0;
  padding-top: var(--gap-sm);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

/* 从点击点轻微展开 */
.feature-card-enter-active,
.feature-card-leave-active {
  transition: transform var(--duration-base) var(--ease-out), opacity var(--duration-base) ease;
}
.feature-card-enter-from,
.feature-card-leave-to {
  transform: scale(0.96);
  opacity: 0;
}
</style>
