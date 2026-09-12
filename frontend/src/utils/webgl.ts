/**
 * WebGL 能力探测。
 *
 * MapLibre GL 强依赖 WebGL：浏览器不提供 WebGL 上下文时，地图 canvas 完全无法渲染，
 * 表现为整块地图区域**全白**（连自绘的业务图层、兜底边界都不会出现）。
 * 最常见的触发场景是无独立显卡的云服务器 / 虚拟机，以及关闭了硬件加速的浏览器。
 */

export interface WebglInfo {
  supported: boolean
  /** 取得最高的 WebGL 版本；0 表示不可用 */
  version: 0 | 1 | 2
  /** 显卡/渲染器名称，便于排查（如 SwiftShader、Microsoft Basic Render Driver） */
  renderer: string
}

function readRenderer(gl: WebGLRenderingContext | WebGL2RenderingContext): string {
  try {
    const ext = gl.getExtension('WEBGL_debug_renderer_info')
    if (!ext) return ''
    return String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) ?? '')
  } catch {
    return ''
  }
}

export function detectWebgl(): WebglInfo {
  if (typeof document === 'undefined') return { supported: false, version: 0, renderer: '' }
  try {
    const canvas = document.createElement('canvas')
    const gl2 = canvas.getContext('webgl2') as WebGL2RenderingContext | null
    if (gl2) return { supported: true, version: 2, renderer: readRenderer(gl2) }
    const gl1 = (canvas.getContext('webgl') ??
      canvas.getContext('experimental-webgl')) as WebGLRenderingContext | null
    if (gl1) return { supported: true, version: 1, renderer: readRenderer(gl1) }
    return { supported: false, version: 0, renderer: '' }
  } catch {
    return { supported: false, version: 0, renderer: '' }
  }
}
