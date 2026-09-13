<script setup lang="ts">
/** 候选地块列表表格（模块 6.3 / 6.5）：行点击与地图双向联动 */
import { computed } from 'vue'
import { useResultStore } from '../../store/result'
import { useMapStore } from '../../store/map'
import { fmtScore } from '../../utils/format'
import CardContainer from '../common/CardContainer.vue'

const result = useResultStore()
const map = useMapStore()

const rows = computed(() => result.response?.candidates ?? [])

/** 表格行点击 → 地图高亮 + 放大居中（详情见地图右侧卡片） */
function onRowClick(row: { rank: number }): void {
  map.selectedRank = map.selectedRank === row.rank ? null : row.rank
}

/** 行样式：得分分级 */
function rowClass({ row }: { row: { rank: number } }): string[] {
  return map.selectedRank === row.rank ? ['is-selected'] : []
}
</script>

<template>
  <CardContainer title="候选地块">
    <template #actions>
      <!-- 空态对齐参考原型 .tag.mute：灰色「0 项」徽标；有结果后显示 Top-N 提示 -->
      <span v-if="!rows.length" class="candidate-table__badge">0 项</span>
      <span v-else class="candidate-table__hint">Top-{{ rows.length }} · 点击行定位地图</span>
    </template>
    <el-table
      v-if="rows.length"
      :data="rows"
      size="small"
      :row-class-name="rowClass"
      @row-click="onRowClick"
      style="width: 100%; cursor: pointer"
    >
      <el-table-column label="编号" width="64">
        <template #default="{ row }">
          <b class="candidate-table__rank">No.{{ row.rank }}</b>
        </template>
      </el-table-column>
      <el-table-column label="综合得分" width="82">
        <template #default="{ row }">
          <span class="candidate-table__score" :data-level="row.score >= 85 ? 'hi' : row.score >= 70 ? 'mid' : 'lo'">
            {{ fmtScore(row.score) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="area_ha" label="面积(ha)" width="74" />
      <el-table-column label="评估">
        <template #default="{ row }">
          <el-tag size="small" :type="row.cluster === 0 ? 'success' : row.cluster === 1 ? 'primary' : 'warning'">
            {{ row.cluster === 0 ? '优先开发' : row.cluster === 1 ? '条件适合' : '储备备用' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    <!-- 空态：复刻参考原型 .empty（地图+放大镜插图 / 标题 / 引导语 / 耗时胶囊） -->
    <div v-else class="candidate-table__empty">
      <svg width="140" height="100" viewBox="0 0 140 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="14" y="34" width="74" height="54" rx="10" fill="#DBEAFE"/>
        <rect x="32" y="18" width="74" height="56" rx="10" fill="#fff" stroke="#BFDBFE" stroke-width="1.4"/>
        <path d="M44 34h30M44 44h20" stroke="#BFDBFE" stroke-width="2.4" stroke-linecap="round"/>
        <rect x="44" y="54" width="18" height="10" rx="3" fill="#EFF6FF"/>
        <rect x="68" y="54" width="18" height="10" rx="3" fill="#EFF6FF"/>
        <circle cx="99" cy="60" r="16" fill="#fff" fill-opacity=".55" stroke="#3B82F6" stroke-width="2.4"/>
        <path d="M111 72l12 12" stroke="#3B82F6" stroke-width="3.4" stroke-linecap="round"/>
        <path d="M99 50c-4 0-7.2 3.1-7.2 6.8 0 4.8 7.2 12.4 7.2 12.4s7.2-7.6 7.2-12.4c0-3.7-3.2-6.8-7.2-6.8z" fill="#3B82F6"/>
        <circle cx="99" cy="56.8" r="2.6" fill="#fff"/>
      </svg>
      <h4>尚未生成候选地块</h4>
      <p>设置偏好后点击「开始选址」，AI 将结合多源数据输出 Top 5 推荐地块及评分依据。</p>
      <span class="candidate-table__pill">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1.2l1.3 3.5L10.8 6 7.3 7.3 6 10.8 4.7 7.3 1.2 6l3.5-1.3z" fill="#3B82F6"/></svg>
        预计耗时 3–5 秒
      </span>
    </div>
  </CardContainer>
</template>

<style scoped>
.candidate-table__hint {
  font-size: 13px;
  color: var(--text-secondary);
}
/* 空态右上角「0 项」徽标（对齐参考原型 .tag.mute） */
.candidate-table__badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: var(--bg-subtle);
  color: var(--text-secondary);
}
/* 空态（对齐参考原型 .empty）：灰底圆角容器 + 插图 + 引导语 + 耗时胶囊 */
.candidate-table__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 250px;
  padding: 20px;
  border-radius: var(--radius-card);
  background: var(--bg-subtle);
  text-align: center;
}
.candidate-table__empty h4 {
  margin: 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary);
}
.candidate-table__empty p {
  margin: 0;
  max-width: 250px;
  font-size: 12px;
  line-height: 19px;
  color: var(--text-secondary);
}
.candidate-table__pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: var(--radius-pill);
  background: #fff;
  border: 1px solid var(--border-lighter);
  font-size: 11px;
  font-weight: 500;
  color: var(--brand);
}
/* 候选地块编号（与地图上的序号标注一一对应）；地块编码只在详情卡片展示 */
.candidate-table__rank {
  color: var(--brand);
  font-weight: 700;
  white-space: nowrap;
}
.candidate-table__score {
  font-weight: 700;
}
.candidate-table__score[data-level='hi'] {
  color: var(--brand-dark-2);
}
.candidate-table__score[data-level='mid'] {
  color: var(--brand);
}
.candidate-table__score[data-level='lo'] {
  color: var(--text-secondary);
}
:deep(.el-table .is-selected) {
  background: var(--brand-light-9);
}
</style>
