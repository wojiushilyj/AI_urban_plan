import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'maplibre-gl/dist/maplibre-gl.css'
import './styles/variables.css'
import './styles/element-theme.css'
import './styles/base.css'
import './styles/layout.css'
import App from './App.vue'
import { pinia } from './store'

const app = createApp(App)
app.use(pinia)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
