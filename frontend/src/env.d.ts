/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  /** 引擎开关：true=前端本地引擎（不依赖后端）；false=调用 FastAPI 后端 */
  readonly VITE_USE_MOCK: string
  /** 天地图 Key，空则降级 OSM */
  readonly VITE_TIANDITU_KEY: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
