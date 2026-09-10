/**
 * 地图浮层定位（点击要素后跟随点击点弹出的卡片）。
 * 纯函数、不依赖 DOM，便于脱离浏览器单测。
 */

export interface CardPlacement {
  /** 锚点：相对容器左上角的像素坐标（对应 MapLibre 的 e.point） */
  anchor: { x: number; y: number }
  cardWidth: number
  /** 卡片实测高度（像素） */
  cardHeight: number
  containerWidth: number
  containerHeight: number
  /** 锚点与卡片之间的偏移（像素），默认 14 */
  offset?: number
  /** 卡片与容器边界的最小留白（像素），默认 12 */
  margin?: number
}

export interface CardPosition {
  left: number
  top: number
}

/**
 * 计算浮层位置：默认落在锚点右下方，越界则翻到锚点另一侧（左上），
 * 最后夹紧在容器内；容器比卡片还小时贴左上留白。
 */
export function placeCard(p: CardPlacement): CardPosition {
  const offset = p.offset ?? 14
  const margin = p.margin ?? 12
  const maxLeft = Math.max(margin, p.containerWidth - p.cardWidth - margin)
  const maxTop = Math.max(margin, p.containerHeight - p.cardHeight - margin)
  let left = p.anchor.x + offset
  let top = p.anchor.y + offset
  if (left > maxLeft) left = p.anchor.x - p.cardWidth - offset
  if (top > maxTop) top = p.anchor.y - p.cardHeight - offset
  return {
    left: Math.max(margin, Math.min(left, maxLeft)),
    top: Math.max(margin, Math.min(top, maxTop)),
  }
}
