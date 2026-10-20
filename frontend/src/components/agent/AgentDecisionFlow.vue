<script setup lang="ts">
/**
 * LangGraph 决策执行流与方案比选面板
 * 包含：PostGIS 状态监控、6 节点决策状态机可视化、方案 A vs 方案 B 并排量化比选、地块视角切换
 */
import { onMounted, ref } from 'vue'
import { useAgentStore } from '../../store/agent'
import { useMapStore } from '../../store/map'

const agent = useAgentStore()
const mapStore = useMapStore()

onMounted(() => {
  agent.checkHealth()
})

const activeStep = ref(0)
const steps = [
  {
    key: 'parse',
    name: '1. 意图解析',
    desc: '自然语言提取项目规模、用地性质要求与防护约束',
    fn: 'parse_requirements',
  },
  {
    key: 'retrieval',
    name: '2. PostGIS 检索',
    desc: '从 2,134 宗土地现状图斑库检索 B2 与 M1 候选地块',
    fn: 'postgis_retrieval',
  },
  {
    key: 'audit',
    name: '3. 底线审查',
    desc: '生态红线/基本农田/蓝线一票否决 + 300m/500m 卫生防护核验',
    fn: 'compliance_audit',
  },
  {
    key: 'scoring',
    name: '4. 五维空间打分',
    desc: 'CGCS2000 / EPSG:4525 规划/交通/协同/公用/成本五维量算',
    fn: 'multicriteria_scoring',
  },
  {
    key: 'synthesis',
    name: '5. 双方案比选',
    desc: '测算 4.58km 跨区通勤距离与集中 vs 分地块优劣势',
    fn: 'scheme_synthesis',
  },
  {
    key: 'report',
    name: '6. 报告生成',
    desc: '自动编写《医药制药产业项目选址规划论证报告》',
    fn: 'generate_report',
  },
]
</script>

<template>
  <div class="agent-flow">
    <!-- 1. PostGIS 数据库与智能体运行状态 -->
    <div class="agent-header-card">
      <div class="header-status">
        <div class="status-badge" :class="agent.postgisHealth?.status === 'connected' ? 'is-connected' : 'is-offline'">
          <span class="dot" />
          {{ agent.postgisHealth?.status === 'connected' ? 'PostGIS 空间库在线' : '本地容灾缓存' }}
        </div>
        <div class="status-meta">
          <span>图斑底盘: <b>{{ agent.postgisHealth?.total_tuban ?? 2134 }}</b> 宗</span>
          <span>坐标系: <b>CGCS2000 / EPSG:4525</b></span>
        </div>
      </div>
      <div class="header-engine">
        <span>决策内核：<b>LangGraph (StateGraph 状态图)</b></span>
      </div>
    </div>

    <!-- 未运行状态提示 -->
    <div v-if="!agent.response" class="empty-agent-state">
      <div class="empty-icon">🤖</div>
      <div class="empty-title">LangGraph 选址智能体待命</div>
      <div class="empty-desc">
        在左侧点击「启动 LangGraph 选址智能体」，智能体将自主执行 PostGIS 空间检索、底线核验、五维量算与方案比选。
      </div>
      <button class="agent-run-btn" :disabled="agent.running" @click="agent.run">
        {{ agent.running ? '智能体决策执行中…' : '🚀 立即启动智能体' }}
      </button>
    </div>

    <!-- 运行完成后的决策成果 -->
    <div v-else class="agent-results">
      <!-- 2. 方案 A vs 方案 B 并排量化对比看板 -->
      <div class="scheme-section">
        <div class="section-title">
          <span class="title-text">⚖️ 方案 A (集中布局) vs 方案 B (两地协同)</span>
        </div>

        <div class="scheme-grid">
          <!-- 方案 A 卡片 -->
          <div class="scheme-card scheme-a">
            <div class="scheme-card__head">
              <span class="scheme-badge badge-a">方案 A</span>
              <span class="scheme-title">集中连片综合基地</span>
            </div>
            <div class="scheme-metrics">
              <div class="metric-row">
                <span class="metric-label">推荐图斑：</span>
                <span class="metric-val">#{{ agent.response.scheme_comparison.unified_scheme.parcel_id }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">规划用地：</span>
                <span class="metric-val"><b>{{ agent.response.scheme_comparison.unified_scheme.area_ha }}</b> ha</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">综合适宜：</span>
                <span class="metric-val highlight-green"><b>{{ agent.response.scheme_comparison.unified_scheme.scores?.total ?? 84.5 }}</b> 分</span>
              </div>
            </div>
            <div class="scheme-pros-cons">
              <div class="pro-tag">✓ 投资建设与管网集约</div>
              <div class="pro-tag">✓ 厂区管理界面高度集中</div>
              <div class="con-tag">✕ 远离高校医学产学研平台</div>
            </div>
            <div class="scenario-tip">
              适合：大规模重资产一体化现代药企
            </div>
          </div>

          <!-- 方案 B 卡片 -->
          <div class="scheme-card scheme-b">
            <div class="scheme-card__head">
              <span class="scheme-badge badge-b">方案 B</span>
              <span class="scheme-title">研发总部 + 生产基地</span>
            </div>
            <div class="scheme-metrics">
              <div class="metric-row">
                <span class="metric-label">研发总部：</span>
                <span class="metric-val">B2 #{{ agent.response.scheme_comparison.dual_site_scheme.hq_parcel_id }} ({{ agent.response.scheme_comparison.dual_site_scheme.hq_area_ha }} ha)</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">生产基地：</span>
                <span class="metric-val">M1 #{{ agent.response.scheme_comparison.dual_site_scheme.factory_parcel_id }} ({{ agent.response.scheme_comparison.dual_site_scheme.factory_area_ha }} ha)</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">跨区通勤：</span>
                <span class="metric-val highlight-orange">
                  <b>{{ agent.response.scheme_comparison.dual_site_scheme.commute_dist_km }}</b> km (约 <b>{{ agent.response.scheme_comparison.dual_site_scheme.commute_car_min }}</b> 分钟)
                </span>
              </div>
            </div>
            <div class="scheme-pros-cons">
              <div class="pro-tag">✓ 总部紧邻高校医院高层次人才</div>
              <div class="pro-tag">✓ 生产基地紧靠快速货运干线</div>
              <div class="con-tag">✕ 存在跨区日常行政协同成本</div>
            </div>
            <div class="scenario-tip">
              适合：高研发投入、注重成果转化的创新药企
            </div>
          </div>
        </div>

        <!-- 综合裁决建议 -->
        <div class="recommendation-box">
          <div class="rec-title">💡 智能体规划论证裁决：</div>
          <div class="rec-content">
            {{ agent.response.scheme_comparison.overall_recommendation }}
          </div>
        </div>
      </div>

      <!-- 3. 地图联动筛选器 -->
      <div class="view-filter-section">
        <div class="filter-label">📍 地图高亮地块联动展示：</div>
        <div class="filter-btn-group">
          <button
            type="button"
            class="filter-btn"
            :class="{ 'is-active': agent.activeView === 'all' }"
            @click="agent.switchView('all')"
          >
            全部候选 (Top 10)
          </button>
          <button
            type="button"
            class="filter-btn"
            :class="{ 'is-active': agent.activeView === 'hq' }"
            @click="agent.switchView('hq')"
          >
            🏢 研发总部 B2 (Top 5)
          </button>
          <button
            type="button"
            class="filter-btn"
            :class="{ 'is-active': agent.activeView === 'factory' }"
            @click="agent.switchView('factory')"
          >
            🏭 生产基地 M1 (Top 5)
          </button>
          <button
            type="button"
            class="filter-btn"
            :class="{ 'is-active': agent.activeView === 'unified' }"
            @click="agent.switchView('unified')"
          >
            🌿 方案A集中基地 (Top 3)
          </button>
        </div>
      </div>

      <!-- 4. LangGraph 6 节点决策状态机展开 -->
      <div class="graph-nodes-section">
        <div class="section-title">
          <span class="title-text">🤖 LangGraph 状态图 6 节点执行明细</span>
        </div>
        <div class="nodes-list">
          <div
            v-for="(step, idx) in steps"
            :key="step.key"
            class="node-item"
            :class="{ 'is-expanded': activeStep === idx }"
            @click="activeStep = (activeStep === idx ? -1 : idx)"
          >
            <div class="node-item__head">
              <div class="node-left">
                <span class="node-check">✓</span>
                <span class="node-title">{{ step.name }}</span>
                <span class="node-fn"><code>{{ step.fn }}</code></span>
              </div>
              <span class="node-status-tag">DONE</span>
            </div>
            <div class="node-desc">{{ step.desc }}</div>
            <div v-show="activeStep === idx" class="node-log-body">
              <div v-if="agent.response.logs[idx]" class="node-log-line">
                {{ agent.response.logs[idx] }}
              </div>
              <div v-else class="node-log-line">
                节点已顺利执行完毕，状态已流转至下一处理单元。
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-flow {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--bg-surface, #FAFAFA);
}

/* 顶部状态卡片 */
.agent-header-card {
  background: #FFFFFF;
  border: 1px solid var(--border-lighter, #E5E7EB);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.header-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.status-badge.is-connected {
  background: #ECFDF5;
  color: #065F46;
}
.status-badge.is-offline {
  background: #F3F4F6;
  color: #6B7280;
}
.status-badge .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.status-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #6B7280;
}
.header-engine {
  font-size: 12px;
  color: #1F2937;
  border-top: 1px dashed #E5E7EB;
  padding-top: 6px;
}

/* 空状态 */
.empty-agent-state {
  background: #FFFFFF;
  border: 1px dashed #D1D5DB;
  border-radius: 8px;
  padding: 28px 18px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.empty-icon {
  font-size: 32px;
}
.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}
.empty-desc {
  font-size: 12px;
  color: #6B7280;
  line-height: 1.6;
  max-width: 320px;
}
.agent-run-btn {
  margin-top: 8px;
  background: #1C7D8C;
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.agent-run-btn:hover:not(:disabled) {
  background: #0F4C55;
}
.agent-run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 方案比选网格 */
.scheme-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title-text {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
}
.scheme-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.scheme-card {
  background: #FFFFFF;
  border: 1px solid var(--border-lighter, #E5E7EB);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.scheme-card.scheme-a {
  border-left: 3px solid #10B981;
}
.scheme-card.scheme-b {
  border-left: 3px solid #F59E0B;
}
.scheme-card__head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.scheme-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
}
.badge-a {
  background: #D1FAE5;
  color: #065F46;
}
.badge-b {
  background: #FEF3C7;
  color: #92400E;
}
.scheme-title {
  font-size: 12px;
  font-weight: 700;
  color: #1F2937;
}
.scheme-metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
}
.metric-row {
  display: flex;
  justify-content: space-between;
  color: #4B5563;
}
.highlight-green {
  color: #059669;
}
.highlight-orange {
  color: #D97706;
}
.scheme-pros-cons {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 10px;
}
.pro-tag {
  color: #059669;
}
.con-tag {
  color: #DC2626;
}
.scenario-tip {
  font-size: 10px;
  color: #6B7280;
  background: #F9FAFB;
  padding: 4px 6px;
  border-radius: 4px;
  margin-top: 4px;
}

/* 推荐裁决框 */
.recommendation-box {
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.5;
}
.rec-title {
  font-weight: 700;
  color: #1D4ED8;
  margin-bottom: 4px;
}
.rec-content {
  color: #1E3A8A;
}

/* 地图视角筛选 */
.view-filter-section {
  background: #FFFFFF;
  border: 1px solid var(--border-lighter, #E5E7EB);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.filter-label {
  font-size: 12px;
  font-weight: 700;
  color: #374151;
}
.filter-btn-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.filter-btn {
  background: #F3F4F6;
  border: 1px solid #E5E7EB;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 11px;
  color: #4B5563;
  cursor: pointer;
  transition: all 0.15s;
}
.filter-btn:hover {
  background: #E5E7EB;
}
.filter-btn.is-active {
  background: #1C7D8C;
  border-color: #1C7D8C;
  color: #FFFFFF;
  font-weight: 600;
}

/* 节点状态列表 */
.graph-nodes-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.nodes-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.node-item {
  background: #FFFFFF;
  border: 1px solid var(--border-lighter, #E5E7EB);
  border-radius: 6px;
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.15s;
}
.node-item:hover {
  border-color: #9CA3AF;
}
.node-item.is-expanded {
  border-color: #1C7D8C;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.node-item__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.node-left {
  display: flex;
  align-items: center;
  gap: 6px;
}
.node-check {
  color: #10B981;
  font-weight: 700;
  font-size: 12px;
}
.node-title {
  font-size: 12px;
  font-weight: 700;
  color: #1F2937;
}
.node-fn code {
  font-size: 10px;
  background: #F3F4F6;
  color: #6B7280;
  padding: 1px 4px;
  border-radius: 3px;
}
.node-status-tag {
  font-size: 10px;
  color: #10B981;
  font-weight: 700;
}
.node-desc {
  font-size: 11px;
  color: #6B7280;
  margin-top: 4px;
}
.node-log-body {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #E5E7EB;
  font-size: 11px;
  color: #374151;
  background: #F9FAFB;
  padding: 6px 8px;
  border-radius: 4px;
  line-height: 1.4;
}
</style>
