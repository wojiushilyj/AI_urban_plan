/**
 * 栅格瓦片可达性探测（底图自检用）。
 *
 * 为什么需要它：MapLibre 的 `map.on('error')` 只告诉我们**某个源失败了**，
 * 无法告诉我们**备选源是否可达**。而"天地图不通就切 OSM"这种兜底，
 * 若备选源同样不通，只是把一种白屏换成另一种白屏 ——
 * 实测：境外出口能取到 OSM、国内直连 OSM 超时，反之天地图在国内正常、
 * 在云机房 IP 上会被 WAF 以 418 拦截。所以切换前必须先探一次。
 *
 * 实测依据（2026-09-12）：MapLibre 4.7.1 中瓦片失败时 ErrorEvent 的传播链为
 * `Source.fire` → `SourceCache` → `Style`（`addSource` 里 `setEventedParent(this, () => ({sourceId: id}))`
 * 注入 sourceId）→ `Map`，因此 `map.on('error')` 能拿到 `sourceId`，可据此筛选底图源。
 */

/** OSM 兜底探测用的固定瓦片：低层级、体积小、CDN 命中率高 */
export const OSM_PROBE_TILE = 'https://tile.openstreetmap.org/3/6/3.png'

/**
 * 探测单个瓦片是否可加载（能取到且能解码为图片即算通）。
 *
 * 只判断"能不能取到图"，不读像素，故不设 `crossOrigin`（设了反而可能被 CORS 拒掉）。
 *
 * @param url 单个**具体**瓦片地址，不要带 `{z}/{x}/{y}` 占位符
 * @param timeoutMs 超时毫秒数，默认 4000
 */
export function probeRasterTile(url: string, timeoutMs = 4000): Promise<boolean> {
  return new Promise((resolve) => {
    let settled = false
    const img = new Image()

    const finish = (ok: boolean): void => {
      if (settled) return
      settled = true
      img.onload = null
      img.onerror = null
      img.src = ''
      resolve(ok)
    }

    const timer = window.setTimeout(() => finish(false), timeoutMs)

    img.onload = () => {
      window.clearTimeout(timer)
      finish(true)
    }
    img.onerror = () => {
      window.clearTimeout(timer)
      finish(false)
    }

    img.src = url
  })
}
