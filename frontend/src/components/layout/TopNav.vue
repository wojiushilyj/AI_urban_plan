<script setup lang="ts">
/**
 * 顶栏（对齐设计稿 .topbar）：63px 高。
 * 结构：品牌（logo 32 + 名称 + AI 徽标）→ 右侧 搜索 / 帮助。
 * 注：通知、头像已按需求移除。
 */
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../../store/app'
import { runStatus, startStatusPolling } from '../../api/system'
import AppIcon from '../common/AppIcon.vue'

const app = useAppStore()
const keyword = ref('')

onMounted(() => startStatusPolling())

function onHelp(): void {
  app.helpVisible = true
}

function onSearch(): void {
  const q = keyword.value.trim()
  ElMessage.info(q ? `搜索「${q}」：地块检索将在对接国土空间规划一张图后开放` : '请输入地块或门类关键词')
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
<p style="color:var(--brand)">研究区：桂林市临桂区；数据来源：国土空间规划真实图层数据。正式应用将对接国土空间规划"一张图"实施监督信息系统。</p>
`
</script>

<template>
  <header class="topnav">
    <!-- 品牌 -->
    <a class="brand" href="#">
      <span class="brand__icon">
        <AppIcon name="brand" :size="32" />
      </span>
      <span class="brand__name">国土AI智慧选址系统</span>
      <span class="brand__badge">AI</span>
    </a>

    <!-- 右侧工具 -->
    <div class="nav-tools">
      <!-- 运行状态灯：提示当前是否接入后台真实算法 -->
      <el-tooltip :content="runStatus.tip" placement="bottom-end" :show-after="200">
        <span class="run-status" :class="`run-status--${runStatus.kind}`">
          <i class="run-status__dot" />
          {{ runStatus.label }}
        </span>
      </el-tooltip>
      <div class="nav-search">
        <AppIcon name="search" :size="16" class="nav-search__icon" />
        <input
          v-model="keyword"
          class="nav-search__input"
          type="text"
          placeholder="搜索地块 / 门类"
          @keydown.enter="onSearch"
        />
      </div>
      <button class="icon-btn" title="帮助" @click="onHelp">
        <AppIcon name="help" :size="20" />
      </button>
    </div>

    <el-dialog v-model="app.helpVisible" title="操作帮助" width="520px" append-to-body>
      <div class="topnav__help" v-html="helpHtml" />
      <template #footer>
        <el-button type="primary" @click="app.helpVisible = false">知道了</el-button>
      </template>
    </el-dialog>
  </header>
</template>

<style scoped>
.topnav {
  display: flex;
  align-items: center;
  gap: 16px;
  height: var(--topnav-height);
  padding: 0 24px;
  background: #FFFFFF;
  border-bottom: 1px solid var(--border-lighter);
}

/* ---- 品牌 ---- */
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}
.brand__icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  filter: drop-shadow(0 2px 6px rgba(37, 99, 235, 0.28));
}
.brand__name {
  font-size: 22px;
  font-weight: 500;
  color: var(--ink);
  letter-spacing: 0.2px;
  white-space: nowrap;
}
.brand__badge {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: var(--brand);
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  line-height: 1.35;
}

/* ---- 右侧工具 ---- */
.nav-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
  margin-left: auto;
}
.nav-search {
  width: 190px;
  height: 40px;
  border-radius: var(--radius-pill);
  background: var(--bg-subtle);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  transition: 0.16s;
}
.nav-search:hover {
  background: var(--border-light);
}
.nav-search__icon {
  color: var(--muted);
  flex: none;
}
.nav-search__input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  font-family: var(--font);
  font-size: 13px;
  color: var(--ink-2);
}
.nav-search__input::placeholder {
  color: var(--muted-2);
}
.icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 0;
  background: var(--bg-subtle);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: 0.16s;
  position: relative;
  color: var(--ink-2);
  flex: none;
}
.icon-btn:hover {
  background: var(--border-light);
}

/* ---- 运行状态灯 ---- */
.run-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  cursor: default;
  user-select: none;
}
.run-status__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  flex: none;
}
/* 演示模式：琥珀 */
.run-status--mock {
  color: #B45309;
  background: #FEF3C7;
  border: 1px solid #FDE68A;
}
/* 算法在线：绿 */
.run-status--online {
  color: #15803D;
  background: #DCFCE7;
  border: 1px solid #BBF7D0;
}
/* 离线 / 检测中：红灰 */
.run-status--offline {
  color: #B91C1C;
  background: #FEE2E2;
  border: 1px solid #FECACA;
}

.topnav__help {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-regular);
  padding: 4px 6px;
}
.topnav__help ol { padding-left: 20px; margin: 6px 0; }

/* 窄屏：搜索框收窄 */
@media (max-width: 1279px) {
  .nav-search { width: 150px; }
}
</style>
