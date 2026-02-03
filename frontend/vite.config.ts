/// <reference types="node" />
import type { ConfigEnv } from 'vite'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// 当通过 nginx 挂到主站子路径 /wisdom-prompt 时，base 必须为 '/wisdom-prompt/'
// 本地单独开发可在 .env 中设置 VITE_BASE_PATH=/ 使用根路径
export default defineConfig((config: ConfigEnv) => {
  const env = loadEnv(config.mode, process.cwd(), '')
  const base = env.VITE_BASE_PATH ?? '/wisdom-prompt/'
  return {
    plugins: [react()],
    base,
    preview: {
      allowedHosts: ['ai-messages.cn', 'localhost'],
    },
  }
})
