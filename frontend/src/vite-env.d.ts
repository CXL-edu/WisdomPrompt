/// <reference types="vite/client" />

// 扩展 Vite 的 ImportMetaEnv，补充本项目子路径部署使用的变量
interface ImportMetaEnv {
  readonly VITE_BASE_PATH?: string
  readonly VITE_API_BASE_URL?: string
}
