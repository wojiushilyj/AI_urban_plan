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
      <span class="candidate-table__hint">{{ rows.length ? `Top-${rows.length} · 点击行定位地图` : '尚未计算' }}</span>
    </template>
    <el-table
      v-if="rows.length"
      :data="rows"
      size="small"
      :row-class-name="rowClass"
      @row-click="onRowClick"
      style="width: 100%; cursor: pointer"
    >
      <el-table-column label="编号" width="96">
        <template #default="{ row }">
          <span class="candidate-table__code">
            <b class="candidate-table__rank">No.{{ row.rank }}</b>
            <span class="candidate-table__code-val">{{ row.code }}</span>
          </span>
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
    <el-empty v-else description="选择行业门类后，点击「开始选址」生成候选地块" :image-size="70" />
  </CardContainer>
</template>

<style scoped>
.candidate-table__hint {
  font-size: 13px;
  color: var(--text-secondary);
}
/* 候选地块编号（与地图上的 No.x 标注一一对应）+ 地块编码 */
.candidate-table__code {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  white-space: nowrap;
}
.candidate-table__rank {
  color: var(--brand);
  font-weight: 700;
}
.candidate-table__code-val {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
  color: var(--text-secondary);
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
