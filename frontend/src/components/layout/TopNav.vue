<script setup lang="ts">
/** 顶栏（v2 简洁蓝白）：品牌 + 帮助 */
import { useAppStore } from '../../store/app'

const app = useAppStore()

function onHelp(): void {
  app.helpVisible = true
}

const helpHtml = `
<p><b>操作流程（3 分钟演示路径）：</b></p>
<ol>
  <li>左侧选择行业门类（如「制造业（装备设备）」）</li>
  <li>在「选址偏好」中设置 5 个维度的在意程度（城市规划/交通物流/产业协同/基础配套/建造成本）</li>
  <li>点击「开始选址」，地图与右侧面板联动查看结果</li>
  <li>右侧「结果列表 / 图表分析」联动查看，点击候选地块查看得分</li>
  <li>「报告导出」一键生成报告，导出 PDF / Excel / 图纸图片</li>
</ol>
<p style="color:#3B82F6">当前为演示样例数据模式（SAMPLE），研究区固定为桂林市临桂区，正式应用将对接国土空间规划"一张图"。</p>
`
</script>

<template>
  <header class="topnav">
    <a class="brand" href="#">
      <span class="brand__icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
          <path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/>
        </svg>
      </span>
      <span class="brand__text">
        <span class="brand__name">国土 AI 智慧选址系统</span>
        <span class="brand__sub">Land.AI Smart Site Selection</span>
      </span>
    </a>

    <div class="topnav__spacer" />

    <div class="topnav__actions">
      <button class="topnav__icon-btn" @click="onHelp" aria-label="帮助">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="18" height="18"><circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01"/></svg>
      </button>

      <!-- 帮助弹窗（保留） -->
      <el-dialog v-model="app.helpVisible" title="操作帮助" width="520px" append-to-body>
        <div class="topnav__help" v-html="helpHtml" />
        <template #footer>
          <el-button type="primary" @click="app.helpVisible = false">知道了</el-button>
        </template>
      </el-dialog>
    </div>
  </header>
</template>

<style scoped>
.topnav {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
  height: var(--topnav-height);
  padding: 0 20px;
  background: #FFFFFF;
  border-bottom: 1px solid var(--border-lighter);
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand__icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--brand);
  color: #fff;
  flex-shrink: 0;
}
.brand__text { display: flex; flex-direction: column; line-height: 1.2; }
.brand__name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}
.brand__sub {
  font-size: 11px;
  color: var(--text-secondary);
  letter-spacing: 0.04em;
  margin-top: 2px;
}
.topnav__spacer { flex: 1; }
.topnav__actions { display: flex; align-items: center; gap: 4px; }
.topnav__icon-btn {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background var(--duration-fast) ease, color var(--duration-fast) ease;
}
.topnav__icon-btn:hover { background: var(--bg-subtle); color: var(--text-primary); }
.topnav__help {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-regular);
  padding: 4px 6px;
}
.topnav__help ol { padding-left: 20px; margin: 6px 0; }
</style>
