<script setup lang="ts">
/**
 * 图标组件（模块 9.3）：lucide 线性图标体系。
 *
 * 几何全部取自设计稿 land-ai-smart-site-meta-blue.html 的原生 viewBox，
 * 只做两处规范化：
 *   1. 原型内写死的颜色（#1F2937 / #6B7280 / #9CA3AF）一律换成 currentColor，
 *      随上下文变色 —— 放在蓝色实底上自动变白，放在卡片标题旁自动变墨色；
 *   2. 原型内承担品牌色的 #3B82F6 换成 var(--brand)，随令牌切换。
 * 描边规范：stroke-width 2 ~ 2.2、圆头圆角（与原型一致）。
 *
 * 用法：<AppIcon name="layers" :size="14" />
 */
import { computed } from 'vue'

/** 可用图标名（原型图标 + 按同语言补齐的缺项） */
export type IconName =
  // 品牌 / 顶栏
  | 'brand' | 'search' | 'help' | 'bell' | 'grid'
  | 'chevron-down' | 'chevron-right'
  // 5 个偏好维度（与 FACTOR_DEFS 一一对应）
  | 'city' | 'truck' | 'network' | 'civic' | 'cost'
  // 地图工具条
  | 'pointer' | 'zoom-in' | 'zoom-out' | 'ruler' | 'polygon' | 'box-select' | 'camera'
  // 底图 / 图层
  | 'layers' | 'layer-grid'
  // 对话
  | 'assistant' | 'send' | 'user' | 'sparkle' | 'bolt' | 'close'
  // 页签 / 导出
  | 'chart-bar' | 'chart-line' | 'file-text' | 'file-pdf' | 'file-sheet' | 'image' | 'play'

interface IconDef {
  /** 原生 viewBox */
  vb: string
  /** 描边宽度（默认 2，对齐原型） */
  sw?: number
  /** SVG 内联内容 */
  body: string
}

const ICONS: Record<string, IconDef> = {
  /* ============ 品牌与顶栏 ============ */
  // 品牌 logo：品牌色圆角方底 + 白色 lucide map（原型 .logo）
  brand: {
    vb: '0 0 32 32',
    body:
      '<rect width="32" height="32" rx="8" fill="var(--brand)"/>' +
      '<g transform="translate(6 6) scale(.8333)" stroke="#FFFFFF" stroke-width="2.4">' +
      '<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/>' +
      '<path d="M9 3v15M15 6v15"/>' +
      '</g>'
  },
  search: {
    vb: '0 0 24 24',
    sw: 2.2,
    body: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4.3-4.3"/>'
  },
  help: {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<circle cx="12" cy="12" r="10"/>' +
      '<path d="M9.1 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>' +
      '<path d="M12 17h.01"/>'
  },
  bell: {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>' +
      '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>'
  },
  // 门类 chip：品牌色圆角方底 + 四个白色小方块（原型 .select 左侧）
  grid: {
    vb: '0 0 22 22',
    body:
      '<rect width="22" height="22" rx="6" fill="var(--brand)"/>' +
      '<g stroke="#FFFFFF" stroke-width="1.5">' +
      '<rect x="5.6" y="5.6" width="4.4" height="4.4" rx="1.1"/>' +
      '<rect x="12" y="5.6" width="4.4" height="4.4" rx="1.1"/>' +
      '<rect x="5.6" y="12" width="4.4" height="4.4" rx="1.1"/>' +
      '<rect x="12" y="12" width="4.4" height="4.4" rx="1.1"/>' +
      '</g>'
  },
  'chevron-down': {
    vb: '0 0 24 24',
    sw: 2.2,
    body: '<path d="M6 9l6 6 6-6"/>'
  },
  'chevron-right': {
    vb: '0 0 24 24',
    sw: 2.4,
    body: '<path d="M9 5l7 7-7 7"/>'
  },

  /* ============ 5 个偏好维度 ============ */
  // 城市规划：楼宇天际线
  city: {
    vb: '0 0 24 24',
    sw: 2.2,
    body:
      '<path d="M3 21h18"/>' +
      '<path d="M5 21V8l7-5 7 5v13"/>' +
      '<path d="M10 21v-5h4v5"/>'
  },
  // 交通物流：厢式货车
  truck: {
    vb: '0 0 24 24',
    sw: 2.2,
    body:
      '<path d="M3 6h10v11H3z"/>' +
      '<path d="M13 9.5h3.6L20 13v4h-7"/>' +
      '<circle cx="7" cy="18.5" r="1.8"/>' +
      '<circle cx="16.5" cy="18.5" r="1.8"/>'
  },
  // 产业协同：三节点连接
  network: {
    vb: '0 0 24 24',
    sw: 2.2,
    body:
      '<circle cx="18" cy="5" r="3"/>' +
      '<circle cx="6" cy="12" r="3"/>' +
      '<circle cx="18" cy="19" r="3"/>' +
      '<path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>'
  },
  // 基础配套：地标建筑
  civic: {
    vb: '0 0 24 24',
    sw: 2.2,
    body:
      '<path d="M3 21h18"/>' +
      '<path d="M5 21V10M10 21V10M14 21V10M19 21V10"/>' +
      '<path d="M12 3l9 5H3z"/>'
  },
  // 建造成本：卡证
  cost: {
    vb: '0 0 24 24',
    sw: 2.2,
    body:
      '<rect x="2.5" y="6" width="19" height="12" rx="2"/>' +
      '<circle cx="12" cy="12" r="2.5"/>' +
      '<path d="M6 12h.01M18 12h.01"/>'
  },

  /* ============ 地图工具条 ============ */
  pointer: { vb: '0 0 24 24', sw: 2, body: '<path d="M4.4 3.2l6.9 17.4 2.5-7.4 7.4-2.5z"/>' },
  'zoom-in': { vb: '0 0 24 24', sw: 2, body: '<path d="M12 5v14M5 12h14"/>' },
  'zoom-out': { vb: '0 0 24 24', sw: 2, body: '<path d="M5 12h14"/>' },
  // 测距：带刻度的直尺
  ruler: {
    vb: '0 0 24 24',
    sw: 1.8,
    body:
      '<path d="M21.3 8.8l-6.1-6.1a1.1 1.1 0 0 0-1.6 0L2.7 13.6a1.1 1.1 0 0 0 0 1.6l6.1 6.1a1.1 1.1 0 0 0 1.6 0l10.9-10.9a1.1 1.1 0 0 0 0-1.6z"/>' +
      '<path d="M7.6 10.6l2 2M10.6 7.6l2 2M13.6 4.6l2 2"/>'
  },
  // 测面：六边形
  polygon: {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M21 16.3v-8.6a2 2 0 0 0-1-1.7l-7-3.9a2 2 0 0 0-2 0l-7 3.9a2 2 0 0 0-1 1.7v8.6a2 2 0 0 0 1 1.7l7 3.9a2 2 0 0 0 2 0l7-3.9a2 2 0 0 0 1-1.7z"/>'
  },
  // 框选：四角选择框
  'box-select': {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M4 9V6a2 2 0 0 1 2-2h3M15 4h3a2 2 0 0 1 2 2v3M20 15v3a2 2 0 0 1-2 2h-3M9 20H6a2 2 0 0 1-2-2v-3"/>'
  },
  // 导出图纸图片（原型未含，按同语言补齐）
  camera: {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M14.5 4h-5L7.5 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3.5z"/>' +
      '<circle cx="12" cy="13" r="3"/>'
  },

  /* ============ 底图 / 图层 ============ */
  layers: {
    vb: '0 0 24 24',
    sw: 2.2,
    body:
      '<path d="M12 3l9 4.8-9 4.8-9-4.8z"/>' +
      '<path d="M3 12.5l9 4.8 9-4.8"/>'
  },
  // 图层：盾牌加号（原型图层行图标）
  'layer-grid': {
    vb: '0 0 24 24',
    sw: 2.2,
    body:
      '<path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z"/>' +
      '<path d="M12 8v8M8 12h8"/>'
  },

  /* ============ 对话与操作 ============ */
  // 选址助手：品牌色圆底 + 白色对话气泡（原型 .chat-head-l）
  assistant: {
    vb: '0 0 28 28',
    body:
      '<circle cx="14" cy="14" r="14" fill="var(--brand)"/>' +
      '<g transform="translate(6.2 6.2) scale(.65)" stroke="#FFFFFF" stroke-width="2.6">' +
      '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' +
      '<path d="M7 8h10M7 12h6"/>' +
      '</g>'
  },
  // 发送：品牌色圆底 + 白色纸飞机（原型 .send）
  send: {
    vb: '0 0 26 26',
    body:
      '<circle cx="13" cy="13" r="13" fill="var(--brand)"/>' +
      '<g transform="translate(5.2 5.2) scale(.65)" stroke="#FFFFFF" stroke-width="2.6">' +
      '<path d="M21.5 2.5L11 13"/>' +
      '<path d="M21.5 2.5l-6.7 18-3.8-7.5-7.5-3.8z"/>' +
      '</g>'
  },
  user: {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<circle cx="12" cy="8" r="4"/>' +
      '<path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>'
  },
  // 四角星：原型空状态胶囊里的 sparkle（实底风格）
  sparkle: {
    vb: '0 0 12 12',
    body: '<path d="M6 1.2l1.3 3.5L10.8 6 7.3 7.3 6 10.8 4.7 7.3 1.2 6l3.5-1.3z" fill="currentColor" stroke="none"/>'
  },
  bolt: { vb: '0 0 24 24', sw: 2, body: '<path d="M13 2L3 14h8l-1 8 12-14h-8l1-8z"/>' },
  close: { vb: '0 0 24 24', sw: 2, body: '<path d="M18 6L6 18M6 6l12 12"/>' },
  // 开始选址：描边三角形（原型 .cta）
  play: { vb: '0 0 24 24', sw: 2.6, body: '<path d="M7 4.5l12 7.5-12 7.5z"/>' },

  /* ============ 页签 / 导出 ============ */
  'chart-bar': {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M3 3v18h18"/>' +
      '<path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>'
  },
  'chart-line': {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M3 3v18h18"/>' +
      '<path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/>'
  },
  'file-text': {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/>' +
      '<path d="M14 2v5h6"/>' +
      '<path d="M16 13H8M16 17H8M10 9H8"/>'
  },
  'file-pdf': {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/>' +
      '<path d="M14 2v5h6"/>' +
      '<path d="M12 11v6M9.5 14.5L12 17l2.5-2.5"/>'
  },
  'file-sheet': {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/>' +
      '<path d="M14 2v5h6"/>' +
      '<path d="M8 12h8M8 16h8M12 12v8"/>'
  },
  image: {
    vb: '0 0 24 24',
    sw: 2,
    body:
      '<rect x="3" y="3" width="18" height="18" rx="2"/>' +
      '<circle cx="9" cy="9" r="2"/>' +
      '<path d="M21 15l-5-5L5 21"/>'
  }
}

const props = withDefaults(
  defineProps<{
    /** 图标名，见 IconName */
    name: string
    /** 显示尺寸（px，宽高一致） */
    size?: number
  }>(),
  { size: 16 }
)

const def = computed<IconDef | undefined>(() => ICONS[props.name])

/* 注册表里用 var(--brand) 表达「这块是品牌色」的意图，
 * 但 var() 写在 SVG 表现属性（fill="var(--brand)"）里 WebKit 不解析，
 * 因此渲染前统一换成 currentColor，再由 .app-icon--brand 提供品牌色。 */
const isBrand = computed(() => def.value?.body.includes('var(--brand)') ?? false)
const body = computed(() => def.value?.body.split('var(--brand)').join('currentColor') ?? '')
</script>

<template>
  <svg
    v-if="def"
    class="app-icon"
    :class="{ 'app-icon--brand': isBrand }"
    :viewBox="def.vb"
    :width="size"
    :height="size"
    fill="none"
    stroke="currentColor"
    :stroke-width="def.sw ?? 2"
    stroke-linecap="round"
    stroke-linejoin="round"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    focusable="false"
    v-html="body"
  />
</template>

<style scoped>
.app-icon {
  display: block;
  flex: none;
  color: inherit;
}
/* 自带品牌色的图标（品牌 logo / 门类 chip / 助手头像 / 发送按钮） */
.app-icon--brand {
  color: var(--brand);
}
</style>
