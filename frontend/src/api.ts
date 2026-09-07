import axios from 'axios'

// 后端地址；开发态走 vite proxy（见 vite.config.ts）
export const api = axios.create({
  baseURL: '/',
  timeout: 60000
})
