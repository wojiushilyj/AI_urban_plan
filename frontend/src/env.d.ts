/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  /** mock 开关：true=前端样例数据模式 */
  readonly VITE_USE_MOCK: string
  /** 天地图 Key，空则降级 OSM */
  readonly VITE_TIANDITU_KEY: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
