/**
 * 结果图层渲染（模块 5.3 / 5.2）：
 * - 候选地块矢量（fill 按 score 分级 + line 边界 + 候选地块序号 ①②③ 标注，
 *   数据来自真实控规工业用地图斑）
 * - 真实业务图层（从 /data/layers/*.geojson 懒加载渲染，见 renderGeoLayers）
 * 底图 style 切换后由调用方 reapplyAll 重挂全部图层。
 */
import type { Map as MlMap } from 'maplibre-gl'
import type { FeatureCollection, Point, Polygon } from 'geojson'
import type { CandidateParcel, SelectionResponse } from '../types/selection'
import type { BusinessLayer } from '../store/map'
import { isLayerId, loadLayer } from '../api/layers'
import { interiorPoint } from '../utils/geo'

export interface LayerHooks {
  onParcelClick?: (parcel: CandidateParcel, lngLat: { lng: number; lat: number }) => void
}

/** 候选地块图层可见性（由图层面板「选址结果」大类控制） */
export interface CandidateVisibility {
  /** 候选地块面 */
  parcels: boolean
  /** 候选地块序号标注（①②③…） */
  labels: boolean
}

/** 标注贴图按 2 倍分辨率绘制，addImage 的 pixelRatio 会把它还原为 1 倍显示尺寸 */
const LABEL_PIXEL_RATIO = 2
/** 序号徽标直径（逻辑像素，屏幕像素，不随缩放变化） */
const LABEL_DIAMETER = 30
/** 徽标描边宽度（逻辑像素） */
const LABEL_STROKE = 2
/**
 * 序号标注贴图 id 前缀。
 * 特意把直径编进 id：调整徽标尺寸后 id 随之改变，否则 MapLibre 的 hasImage 会命中
 * 热更新 / 底图切换后残留的旧贴图，跳过重新注册，新尺寸不会生效。
 */
const LABEL_IMAGE_PREFIX = `parcel-label-idx${LABEL_DIAMETER}-`

/**
 * 把候选地块序号绘制成圆形徽标贴图（白字蓝底圆标，视觉上即 ①②③）。
 *
 * 不使用 symbol 的 text-field：底图样式是 OSM / 天地图**栅格**样式，没有 glyphs 字体服务，
 * 文本会静默丢失。canvas 贴图零依赖、离线可用，且能被 preserveDrawingBuffer 的图纸导出捕获。
 *
 * 也不用 Unicode 的 ① 字形：① 自带一个圆圈，再叠加徽标底圈会出现「圈套圈」，
 * 且该字形在部分系统字体下缺字。直接画圆 + 数字，跨平台稳定。
 */
function makeBadgeImage(rank: number): ImageData {
  const text = String(rank)
  const d = LABEL_DIAMETER
  // 字号随直径缩放：一位数占直径 60%，两位数略小以留出左右留白
  const fontSize = Math.round(d * (text.length > 1 ? 0.47 : 0.6))
  const font = (size: number) =>
    `700 ${size}px "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif`
  const canvas = document.createElement('canvas')
  canvas.width = d * LABEL_PIXEL_RATIO
  canvas.height = d * LABEL_PIXEL_RATIO
  const ctx = canvas.getContext('2d') as CanvasRenderingContext2D
  // 改动 canvas 尺寸会重置上下文状态，缩放/字体/对齐都需在此之后设置
  ctx.scale(LABEL_PIXEL_RATIO, LABEL_PIXEL_RATIO)
  ctx.beginPath()
  // 半径内缩描边的一半，让描边外沿正好落在贴图边界内
  ctx.arc(d / 2, d / 2, d / 2 - LABEL_STROKE / 2, 0, Math.PI * 2)
  ctx.fillStyle = '#3B82F6'
  ctx.fill()
  ctx.lineWidth = LABEL_STROKE
  ctx.strokeStyle = '#FFFFFF'
  ctx.stroke()
  ctx.font = font(fontSize)
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#FFFFFF'
  ctx.fillText(text, d / 2, d / 2 + fontSize * 0.04)
  return ctx.getImageData(0, 0, canvas.width, canvas.height)
}

export function useMapLayers(getMap: () => MlMap | null, hooks: LayerHooks = {}) {
  function addSource(id: string, data: unknown): void {
    const m = getMap()
    if (!m) return
    if (!m.getSource(id)) m.addSource(id, { type: 'geojson', data: data as never })
    else (m.getSource(id) as maplibregl.GeoJSONSource).setData(data as never)
  }

  function removeLayers(ids: string[]): void {
    const m = getMap()
    if (!m) return
    for (const id of ids) if (m.getLayer(id)) m.removeLayer(id)
  }

  /** 候选地块矢量 + 序号标注（模块 5.3） */
  function renderCandidates(
    result: SelectionResponse,
    selectedRank: number | null,
    vis: CandidateVisibility
  ): void {
    const m = getMap()
    if (!m) return

    const parcels: FeatureCollection<Polygon, { rank: number; score: number; code: string; parcel: string }> = {
      type: 'FeatureCollection',
      features: result.candidates.map((c) => ({
        type: 'Feature',
        geometry: c.geometry,
        properties: { rank: c.rank, score: c.score, code: c.code ?? '', parcel: JSON.stringify(c) },
      })),
    }
    // 候选地块序号（①②③…）标注挂在图斑内点上（而非面要素）：
    // 面要素的标注锚点由 MapLibre 内部推算，用内点可保证标注始终落在图斑内部。
    const labels: FeatureCollection<Point, { rank: number; image: string }> = {
      type: 'FeatureCollection',
      features: result.candidates.map((c) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: interiorPoint(c.geometry) },
        properties: { rank: c.rank, image: LABEL_IMAGE_PREFIX + c.rank },
      })),
    }

    // 序号贴图：底图 style 切换会清空已注册图片，此处按需补建
    for (const f of labels.features) {
      if (m.hasImage(f.properties.image)) continue
      try {
        m.addImage(f.properties.image, makeBadgeImage(f.properties.rank), {
          pixelRatio: LABEL_PIXEL_RATIO,
        })
      } catch (e) {
        // style 尚未就绪时先跳过，下一次 reapplyAll 会补上
        console.warn('[候选地块] 序号贴图注册失败：', e)
      }
    }

    addSource('candidates-src', parcels)
    addSource('candidates-label-src', labels)

    // 面 / 边界（仅在首次创建，后续只更新 paint，避免反复增删图层）
    if (!m.getLayer('candidates-fill')) {
      m.addLayer({
        id: 'candidates-fill',
        type: 'fill',
        source: 'candidates-src',
        paint: {
          'fill-color': [
            'interpolate', ['linear'], ['get', 'score'],
            55, '#BFDBFE', 70, '#93C5FD', 85, '#3B82F6', 95, '#2563EB',
          ],
          'fill-opacity': 0.5,
        },
      })
    }
    if (!m.getLayer('candidates-line')) {
      m.addLayer({
        id: 'candidates-line',
        type: 'line',
        source: 'candidates-src',
        paint: { 'line-color': '#3B82F6', 'line-width': 1.5 },
      })
    }
    // 序号标注（symbol + icon-image，不依赖 glyphs）
    if (!m.getLayer('candidates-label')) {
      m.addLayer({
        id: 'candidates-label',
        type: 'symbol',
        source: 'candidates-label-src',
        layout: {
          'icon-image': ['get', 'image'],
          'icon-size': 1,
          // 候选地块数量少（Top-N），不做避让，保证序号全部可见
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
          // 名次靠前的压在上层
          'symbol-sort-key': ['-', 100, ['get', 'rank']],
        },
      })
    }

    // 选中地块：更实的面 + 红色加粗描边
    const sel = selectedRank ?? -1
    m.setPaintProperty('candidates-fill', 'fill-opacity', ['case', ['==', ['get', 'rank'], sel], 0.72, 0.45])
    m.setPaintProperty('candidates-line', 'line-color', ['case', ['==', ['get', 'rank'], sel], '#EF4444', '#3B82F6'])
    m.setPaintProperty('candidates-line', 'line-width', ['case', ['==', ['get', 'rank'], sel], 4, 1.5])

    // 图层面板开关 → 可见性
    m.setLayoutProperty('candidates-fill', 'visibility', vis.parcels ? 'visible' : 'none')
    m.setLayoutProperty('candidates-line', 'visibility', vis.parcels ? 'visible' : 'none')
    m.setLayoutProperty('candidates-label', 'visibility', vis.labels ? 'visible' : 'none')

    if (hooks.onParcelClick) {
      m.off('click', 'candidates-fill', onFillClick)
      m.on('click', 'candidates-fill', onFillClick)
    }
  }

  function onFillClick(e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }): void {
    const raw = e.features?.[0]?.properties?.['parcel']
    if (!raw || !hooks.onParcelClick) return
    const parcel = JSON.parse(String(raw)) as CandidateParcel
    hooks.onParcelClick(parcel, e.lngLat)
  }

  /**
   * 可拾取的图层 id 列表（按渲染顺序，靠后的压在上层）。
   * 含真实业务图层与候选地块面；不存在的图层自动跳过。
   */
  function pickLayers(defs: BusinessLayer[]): string[] {
    const m = getMap()
    if (!m) return []
    const ids = defs.filter((d) => d.kind === 'geojson').map((d) => `${d.id}-layer`)
    ids.push('candidates-fill')
    return ids.filter((id) => m.getLayer(id))
  }

  /**
   * 拾取点击位置最上层的要素（工具条「要素查询」模式用）。
   *
   * queryRenderedFeatures 的返回顺序不做保证，因此按图层叠加顺序逐个查询，
   * 取最后一个命中的图层（最后添加的绘制在最上层）作为拾取结果。
   */
  function pickTop(
    e: maplibregl.MapMouseEvent,
    ids: string[]
  ): { layerId: string; feature: maplibregl.MapGeoJSONFeature } | null {
    const m = getMap()
    if (!m) return null
    let hit: { layerId: string; feature: maplibregl.MapGeoJSONFeature } | null = null
    for (const id of ids) {
      const fs = m.queryRenderedFeatures(e.point, { layers: [id] })
      if (fs.length) hit = { layerId: id, feature: fs[0] }
    }
    return hit
  }

  /** AOI 边界（模块 5.4 框选结果回显） */
  function renderAoi(aoi: Polygon | null): void {
    const m = getMap()
    if (!m || !aoi) return
    addSource('aoi-src', { type: 'Feature', geometry: aoi, properties: {} })
    removeLayers(['aoi-fill', 'aoi-line'])
    m.addLayer({
      id: 'aoi-fill',
      type: 'fill',
      source: 'aoi-src',
      paint: { 'fill-color': '#3B82F6', 'fill-opacity': 0.06 },
    })
    m.addLayer({
      id: 'aoi-line',
      type: 'line',
      source: 'aoi-src',
      paint: { 'line-color': '#3B82F6', 'line-width': 2, 'line-dasharray': [3, 2] },
    })
  }

  /** 真实业务图层（模块 5.2）：从 /data/layers/*.geojson 懒加载，首次可见时才请求数据 */
  async function renderGeoLayers(defs: BusinessLayer[]): Promise<void> {
    const m = getMap()
    if (!m) return
    // 语义配色：耕地橙黄、红线红、水系蓝、绿地绿、产业橙紫、设施青、文保深红、交通灰红
    interface LayerStyle {
      color: string
      opacity: number
      type: 'fill' | 'circle' | 'line'
      /** 线图层自定义 paint（按属性分级着色/定宽），提供时覆盖 color/opacity */
      linePaint?: Record<string, unknown>
      /** 面图层自定义 paint（按属性分级着色），提供时覆盖 color/opacity */
      fillPaint?: Record<string, unknown>
    }
    const styleMap: Record<string, LayerStyle> = {
      'perm-farmland': { color: '#F59E0B', opacity: 0.35, type: 'fill' },
      'eco-redline': { color: '#EF4444', opacity: 0.3, type: 'fill' },
      'urban-boundary': { color: '#8B5CF6', opacity: 0.25, type: 'fill' },
      'yellow-line': { color: '#EAB308', opacity: 0.3, type: 'fill' },
      'blue-line': { color: '#3B82F6', opacity: 0.3, type: 'fill' },
      'green-line': { color: '#22C55E', opacity: 0.3, type: 'fill' },
      'industrial-land': { color: '#D97706', opacity: 0.35, type: 'fill' },
      // 现状工业用地用深褐，与规划口径的亮橙（工业用地/控规工业用地）区分
      'current-industrial-land': { color: '#78350F', opacity: 0.3, type: 'fill' },
      'regulated-industrial': { color: '#EA580C', opacity: 0.35, type: 'fill' },
      'industrial-park': { color: '#7C3AED', opacity: 0.35, type: 'fill' },
      // 交通设施：路网按道路等级分级着色（高速红 / 快速橙 / 公路黄 / 城市道路灰 / 铁路紫）
      'road-network': {
        color: '#94A3B8',
        opacity: 0.85,
        type: 'line',
        linePaint: {
          'line-color': [
            'match', ['get', '道路等级'],
            '高速公路', '#DC2626',
            '快速路', '#EA580C',
            '一级公路', '#F59E0B',
            '二级公路', '#F59E0B',
            '主干路', '#64748B',
            '次干路', '#94A3B8',
            '支路', '#CBD5E1',
            '#7C3AED', // 其余（铁路-普铁/高铁/市域）
          ],
          'line-width': [
            'match', ['get', '道路等级'],
            '高速公路', 3,
            '快速路', 2.6,
            '一级公路', 2,
            '二级公路', 2,
            '主干路', 1.6,
            '次干路', 1.2,
            '支路', 0.9,
            1.6,
          ],
          'line-opacity': 0.85,
        },
      },
      'highway-interchange': { color: '#991B1B', opacity: 0.95, type: 'circle' },
      'freight-station': { color: '#0D9488', opacity: 0.45, type: 'fill' },
      'prod-service-point': { color: '#06B6D4', opacity: 0.9, type: 'circle' },
      'prod-service-area': { color: '#0EA5E9', opacity: 0.4, type: 'fill' },
      'cultural-relic': { color: '#DC2626', opacity: 0.5, type: 'fill' },
      // 市政设施：按国标用地代码（字段前 4 位）区分电力/给水/排水/燃气/通信/邮政/水工
      // 用 slice 而非匹配完整字符串，可兼容「1303供电用电」这类录入不一致的值
      'municipal-land': {
        color: '#0891B2',
        opacity: 0.55,
        type: 'fill',
        fillPaint: {
          'fill-color': [
            'match', ['slice', ['get', '用地'], 0, 4],
            '1301', '#38BDF8', // 供水
            '1302', '#0284C7', // 排水
            '1303', '#FACC15', // 供电
            '1304', '#FB923C', // 供燃气
            '1306', '#A78BFA', // 通信
            '1307', '#22C55E', // 邮政
            '1311', '#0891B2', // 水工设施
            '#0891B2',
          ],
          'fill-opacity': 0.55,
          'fill-outline-color': '#0E7490',
        },
      },
      // 现状建筑：按层数分级（1 层浅灰 → 3 层深灰），作为现状底衬不抢主体图层
      'current-building': {
        color: '#FDE68A',
        opacity: 0.4,
        type: 'fill',
        fillPaint: {
          // 柔和鹅黄，按层数分级：层数越高颜色越深
          'fill-color': [
            'match', ['get', '层数'],
            1, '#FEF3C7',
            2, '#FDE68A',
            3, '#FBBF24',
            '#FEF3C7',
          ],
          'fill-opacity': 0.4,
          'fill-outline-color': '#B45309',
        },
      },
    }

    for (const def of defs) {
      if (def.kind !== 'geojson' || !def.sourceUrl) continue
      const style = styleMap[def.id]
      if (!style) continue
      const srcId = `${def.id}-src`
      const layerId = `${def.id}-layer`

      // 懒加载：仅当图层首次可见时才请求数据（大图层如永久基本农田 7MB 按需加载）
      if (!m.getSource(srcId) && def.visible) {
        try {
          if (!isLayerId(def.id)) throw new Error(`未登记的图层 id：${def.id}`)
          // 与选址计算共用同一份缓存（见 api/layers.ts）
          const data = await loadLayer(def.id)
          m.addSource(srcId, { type: 'geojson', data: data as never })
          if (style.type === 'circle') {
            m.addLayer({
              id: layerId,
              type: 'circle',
              source: srcId,
              layout: { visibility: 'visible' },
              paint: {
                'circle-radius': 6,
                'circle-color': style.color,
                'circle-opacity': style.opacity,
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 1.5,
              },
            })
          } else if (style.type === 'line') {
            m.addLayer({
              id: layerId,
              type: 'line',
              source: srcId,
              layout: { visibility: 'visible', 'line-cap': 'round', 'line-join': 'round' },
              paint: (style.linePaint ?? {
                'line-color': style.color,
                'line-width': 1.5,
                'line-opacity': style.opacity,
              }) as never,
            })
          } else {
            m.addLayer({
              id: layerId,
              type: 'fill',
              source: srcId,
              layout: { visibility: 'visible' },
              paint: (style.fillPaint ?? {
                'fill-color': style.color,
                'fill-opacity': style.opacity,
                'fill-outline-color': style.color,
              }) as never,
            })
          }
        } catch (e) {
          console.warn(`[图层] ${def.id} 加载失败：`, e)
          continue
        }
      }

      // 切换可见性
      if (m.getLayer(layerId)) {
        m.setLayoutProperty(layerId, 'visibility', def.visible ? 'visible' : 'none')
      }
    }
  }

  return { renderCandidates, renderAoi, renderGeoLayers, removeLayers, pickLayers, pickTop }
}
