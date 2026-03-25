<template>
  <div class="selection-page">
    <div class="page-header">
      <div class="header-left">
        <h1>策略选股</h1>
        <p class="subtitle">使用条件组组合技术指标、基本面和形态信号，统一周期进行实时筛选。</p>
      </div>
      <div class="header-right">
        <span class="last-updated">{{ running ? '预览刷新中' : '预览已同步' }}</span>
        <button class="btn btn-primary" :disabled="running" @click="runSelection(true)">
          {{ running ? '筛选中...' : '立即筛选' }}
        </button>
      </div>
    </div>

    <section class="card workspace-card">
      <div class="workspace-grid">
        <label class="field field-medium">
          <span>条件方案</span>
          <select v-model="selectedPresetId" @change="handlePresetChange">
            <option value="">当前未绑定方案</option>
            <option v-for="preset in presets" :key="preset.id" :value="String(preset.id)">
              {{ preset.name }}
            </option>
          </select>
        </label>

        <label class="field field-small">
          <span>周期</span>
          <select v-model="period" @change="schedulePreview">
            <option v-for="periodItem in catalog?.periods || []" :key="periodItem.key" :value="periodItem.key">
              {{ periodItem.label }}
            </option>
          </select>
        </label>

        <label class="field field-grow">
          <span>方案名称</span>
          <input v-model.trim="presetName" type="text" placeholder="例如：日线趋势突破" />
        </label>

        <div class="toolbar-actions">
          <button class="btn btn-secondary" @click="resetTemplate">新方案</button>
          <button class="btn btn-secondary" @click="savePreset(false)">保存</button>
          <button class="btn btn-secondary" @click="savePreset(true)">另存为</button>
          <button class="btn btn-danger" :disabled="!selectedPresetId" @click="deletePreset">删除</button>
        </div>
      </div>

      <div class="workspace-meta">
        <span class="meta-chip guide-chip">1. 选择方案与周期</span>
        <span class="meta-chip guide-chip">2. 添加条件并配置参数</span>
        <span class="meta-chip guide-chip">3. 点击立即筛选查看结果</span>
        <span class="meta-chip">条件 {{ totalConditions }}</span>
        <span class="meta-chip">周期 {{ periodLabel }}</span>
        <span v-if="resultMeta.trade_date" class="meta-chip">最近筛选 {{ resultMeta.trade_date }}</span>
        <span v-for="group in catalog?.groups || []" :key="group.key" class="meta-chip">
          {{ group.label }} {{ group.items.length }}
        </span>
      </div>
    </section>

    <div class="selection-layout">
      <section class="card builder-card">
        <div class="card-header">
          <div>
            <h3>条件编辑</h3>
            <p>所有逻辑都在条件组中完成。每个条件都支持参数、左右值比较和最近 N 周期判断。</p>
          </div>
          <div class="header-tags">
            <span class="status-chip">支持 AND / OR / NOT</span>
          </div>
        </div>

        <SelectionRuleTree
          :node="rootRule"
          :depth="0"
          :metric-map="metricMap"
          :operator-labels="operatorLabels"
          @add-condition="openNewCondition"
          @add-group="addGroup"
          @edit-condition="openExistingCondition"
          @remove-node="removeNode"
          @update-group="updateGroup"
        />
      </section>

      <section class="card results-card">
        <div class="card-header">
          <div>
            <h3>筛选结果</h3>
            <p v-if="resultMeta.trade_date">{{ resultMeta.trade_date }} · {{ periodLabel }} · 共 {{ results.length }} 只股票</p>
            <p v-else>配置好条件后，点击“立即筛选”，或者等待自动预览刷新。</p>
          </div>
          <div class="header-tags">
            <span class="status-chip accent">{{ results.length }} 只</span>
          </div>
        </div>

        <div v-if="!results.length" class="empty-state">
          <h4>当前没有命中结果</h4>
          <p>先在左侧添加条件，或者切换到一个已有方案。</p>
        </div>

        <div v-else class="results-table-wrapper">
          <table class="results-table">
            <thead>
              <tr>
                <th>股票</th>
                <th>信号</th>
                <th>收盘价</th>
                <th>涨跌幅</th>
                <th>条件命中</th>
                <th>评分</th>
                <th>命中说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in results" :key="item.ts_code" class="result-row" @click="$router.push(`/stock/${item.code}`)">
                <td>
                  <div class="stock-cell">
                    <span class="stock-code">{{ item.code }}</span>
                    <strong>{{ item.stock_name }}</strong>
                  </div>
                </td>
                <td>
                  <span class="signal-chip" :class="getSignalClass(item.signal)">
                    {{ formatSignalLabel(item.signal) }}
                  </span>
                </td>
                <td>{{ formatNumber(item.snapshot?.close) }}</td>
                <td :class="['change-cell', { positive: Number(item.snapshot?.pct_chg || 0) >= 0, negative: Number(item.snapshot?.pct_chg || 0) < 0 }]">
                  {{ formatSigned(item.snapshot?.pct_chg) }}%
                </td>
                <td>{{ item.matched_conditions || 0 }}/{{ item.total_conditions || 0 }}</td>
                <td class="score-cell">{{ item.score.toFixed(2) }}</td>
                <td>
                  <div class="explanation-list">
                    <span v-for="explanation in item.explanations?.slice(0, 2) || []" :key="explanation.id" class="explanation-chip">
                      {{ explanation.label || explanation.metric_key }} {{ operatorLabels[explanation.operator] || explanation.operator }} {{ formatScalar(explanation.match_right) }}
                    </span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <SelectionConditionModal
      :visible="conditionModalVisible"
      :catalog="catalog"
      :initial-node="editingCondition"
      @close="closeConditionModal"
      @save="saveCondition"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, ref } from 'vue'
import { selectionApi } from '@/api'
import SelectionConditionModal from '@/components/selection/SelectionConditionModal.vue'
import SelectionRuleTree from '@/components/selection/SelectionRuleTree.vue'
import type {
  CatalogMetric,
  ConditionNode,
  GroupNode,
  SelectionCatalog,
  SelectionPreset,
  SelectionResultItem,
  SelectionRunResponse,
  SelectionNode,
} from '@/components/selection/types'

const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')

const catalog = ref<SelectionCatalog | null>(null)
const presets = ref<SelectionPreset[]>([])
const results = ref<SelectionResultItem[]>([])
const running = ref(false)
const period = ref<'daily' | 'weekly' | 'monthly'>('daily')
const presetName = ref('未命名方案')
const selectedPresetId = ref('')
const rootRule = ref<GroupNode>(createEmptyGroup())
const conditionModalVisible = ref(false)
const editingCondition = ref<ConditionNode | null>(null)
const editingParentId = ref<string | null>(null)
const editingNodeId = ref<string | null>(null)
const resultMeta = ref<{ trade_date: string | null }>({ trade_date: null })
let previewTimer: number | null = null

const metricMap = computed<Record<string, CatalogMetric>>(() => Object.fromEntries((catalog.value?.groups || []).flatMap((group) => group.items).map((metric) => [metric.key, metric])))
const operatorLabels = computed<Record<string, string>>(() => Object.fromEntries((catalog.value?.operators || []).map((operator) => [operator.key, operator.label])))
const periodLabel = computed(() => catalog.value?.periods.find((item) => item.key === period.value)?.label || period.value)
const totalConditions = computed(() => countConditions(rootRule.value))

function generateId() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `node_${Math.random().toString(36).slice(2, 10)}`
}

function createEmptyGroup(): GroupNode {
  return {
    node_type: 'group',
    id: generateId(),
    label: '主条件组',
    combinator: 'and',
    children: [],
  }
}

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function buildDefaultCondition(metric?: CatalogMetric): ConditionNode {
  const targetMetric = metric || catalog.value?.groups[0]?.items[0]
  const output = targetMetric?.outputs[0]
  return {
    node_type: 'condition',
    id: generateId(),
    label: targetMetric?.label,
    left: {
      source_type: 'indicator',
      metric_key: targetMetric?.key || 'close',
      output_key: targetMetric?.default_output || output?.key || 'value',
      params: Object.fromEntries((targetMetric?.params || []).map((param) => [param.key, param.default])),
    },
    operator: targetMetric?.operators[0] || 'gt',
    right: {
      source_type: 'value',
      value: output?.kind === 'boolean' ? true : 0,
    },
    time_rule: {
      mode: 'current',
      lookback: 1,
    },
    weight: 1,
  }
}

function countConditions(node: SelectionNode): number {
  if (node.node_type === 'condition') return 1
  return node.children.reduce((sum, child) => sum + countConditions(child), 0)
}

function findNode(node: SelectionNode, id: string): SelectionNode | null {
  if (node.id === id) return node
  if (node.node_type === 'condition') return null
  for (const child of node.children) {
    const found = findNode(child, id)
    if (found) return found
  }
  return null
}

function addNodeToGroup(node: GroupNode, groupId: string, child: SelectionNode): boolean {
  if (node.id === groupId) {
    node.children.push(child)
    return true
  }
  for (const item of node.children) {
    if (item.node_type === 'group' && addNodeToGroup(item, groupId, child)) {
      return true
    }
  }
  return false
}

function replaceNode(node: GroupNode, nodeId: string, nextNode: SelectionNode): boolean {
  const index = node.children.findIndex((child) => child.id === nodeId)
  if (index >= 0) {
    node.children.splice(index, 1, nextNode)
    return true
  }
  for (const child of node.children) {
    if (child.node_type === 'group' && replaceNode(child, nodeId, nextNode)) {
      return true
    }
  }
  return false
}

function removeNodeFromGroup(node: GroupNode, nodeId: string): boolean {
  const index = node.children.findIndex((child) => child.id === nodeId)
  if (index >= 0) {
    node.children.splice(index, 1)
    return true
  }
  for (const child of node.children) {
    if (child.node_type === 'group' && removeNodeFromGroup(child, nodeId)) {
      return true
    }
  }
  return false
}

async function fetchCatalog() {
  catalog.value = await selectionApi.getConditions()
  if (!catalog.value?.periods.find((item) => item.key === period.value)) {
    period.value = catalog.value?.periods[0]?.key || 'daily'
  }
}

async function fetchPresets() {
  presets.value = await selectionApi.getMyConditions()
}

function hydrateFromPreset(preset: SelectionPreset) {
  const template = preset.params || {}
  selectedPresetId.value = String(preset.id)
  presetName.value = preset.name
  period.value = template.period || 'daily'
  rootRule.value = cloneValue(template.root || createEmptyGroup())
  results.value = []
  resultMeta.value = { trade_date: null }
}

function resetTemplate() {
  selectedPresetId.value = ''
  presetName.value = '未命名方案'
  rootRule.value = createEmptyGroup()
  period.value = catalog.value?.periods[0]?.key || 'daily'
  results.value = []
  resultMeta.value = { trade_date: null }
}

async function handlePresetChange() {
  const preset = presets.value.find((item) => String(item.id) === selectedPresetId.value)
  if (!preset) {
    resetTemplate()
    return
  }
  hydrateFromPreset(preset)
  await runSelection(false)
}

function buildTemplate() {
  return {
    version: 1,
    name: presetName.value,
    period: period.value,
    root: cloneValue(rootRule.value),
  }
}

async function savePreset(asCopy: boolean) {
  try {
    let name = presetName.value.trim() || '未命名方案'
    if (asCopy || !selectedPresetId.value) {
      const input = window.prompt('方案名称', name)
      if (!input) return
      name = input.trim() || name
    }
    const payload = {
      name,
      category: 'template',
      description: `条件方案 · ${periodLabel.value}`,
      params: buildTemplate(),
      is_active: true,
    }
    if (selectedPresetId.value && !asCopy) {
      await selectionApi.updateMyCondition(Number(selectedPresetId.value), payload)
      showNotification?.('success', '方案已更新')
    } else {
      await selectionApi.createMyCondition(payload)
      showNotification?.('success', '方案已保存')
    }
    await fetchPresets()
    const preset = presets.value.find((item) => item.name === name)
    if (preset) selectedPresetId.value = String(preset.id)
    presetName.value = name
  } catch (error) {
    console.error(error)
    showNotification?.('error', '保存方案失败')
  }
}

async function deletePreset() {
  if (!selectedPresetId.value) return
  if (!window.confirm('确定删除当前方案吗？')) return
  try {
    await selectionApi.deleteMyCondition(Number(selectedPresetId.value))
    showNotification?.('success', '方案已删除')
    await fetchPresets()
    resetTemplate()
  } catch (error) {
    console.error(error)
    showNotification?.('error', '删除方案失败')
  }
}

async function runSelection(persistResult = false) {
  running.value = true
  try {
    const response = await selectionApi.runSelection({
      template: buildTemplate(),
      persist_result: persistResult,
      limit: 200,
    }) as SelectionRunResponse | SelectionResultItem[]
    if (Array.isArray(response)) {
      results.value = response
      resultMeta.value = { trade_date: response[0]?.trade_date || null }
    } else {
      results.value = response.items || []
      resultMeta.value = { trade_date: response.trade_date || null }
    }
  } catch (error) {
    console.error(error)
    showNotification?.('error', '执行筛选失败')
  } finally {
    running.value = false
  }
}

function schedulePreview() {
  if (previewTimer) window.clearTimeout(previewTimer)
  previewTimer = window.setTimeout(() => {
    runSelection(false)
  }, 450)
}

function openNewCondition(groupId: string) {
  editingNodeId.value = null
  editingParentId.value = groupId
  editingCondition.value = buildDefaultCondition(catalog.value?.groups[0]?.items[0])
  conditionModalVisible.value = true
}

function openExistingCondition(nodeId: string) {
  const node = findNode(rootRule.value, nodeId)
  if (!node || node.node_type !== 'condition') return
  editingNodeId.value = nodeId
  editingParentId.value = null
  editingCondition.value = cloneValue(node)
  conditionModalVisible.value = true
}

function closeConditionModal() {
  conditionModalVisible.value = false
  editingCondition.value = null
  editingNodeId.value = null
  editingParentId.value = null
}

function saveCondition(condition: ConditionNode) {
  if (editingNodeId.value) {
    replaceNode(rootRule.value, editingNodeId.value, condition)
  } else if (editingParentId.value) {
    addNodeToGroup(rootRule.value, editingParentId.value, condition)
  }
  closeConditionModal()
  schedulePreview()
}

function addGroup(groupId: string) {
  addNodeToGroup(rootRule.value, groupId, {
    node_type: 'group',
    id: generateId(),
    label: '子条件组',
    combinator: 'and',
    children: [],
  })
  schedulePreview()
}

function removeNode(nodeId: string) {
  removeNodeFromGroup(rootRule.value, nodeId)
  schedulePreview()
}

function updateGroup(payload: { id: string; combinator: 'and' | 'or' | 'not' }) {
  const node = findNode(rootRule.value, payload.id)
  if (!node || node.node_type !== 'group') return
  node.combinator = payload.combinator
  schedulePreview()
}

function formatNumber(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return Number(value).toFixed(2)
}

function formatSigned(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const number = Number(value)
  return `${number >= 0 ? '+' : ''}${number.toFixed(2)}`
}

function formatScalar(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === '') return '--'
  if (typeof value === 'number') return value.toFixed(2)
  return String(value)
}

function getSignalClass(signal?: string | null) {
  const text = (signal || '').toLowerCase()
  if (text.includes('buy') || text.includes('bull') || text.includes('多') || text.includes('涨')) return 'bullish'
  if (text.includes('sell') || text.includes('bear') || text.includes('空') || text.includes('跌')) return 'bearish'
  return 'neutral'
}

function formatSignalLabel(signal?: string | null) {
  if (!signal) return '中性'
  const text = String(signal)
  if (text === 'buy') return '看多'
  if (text === 'sell') return '看空'
  if (text === 'hold') return '观察'
  return text
}

onMounted(async () => {
  await fetchCatalog()
  await fetchPresets()
  if (presets.value.length) {
    hydrateFromPreset(presets.value[0])
    await runSelection(false)
  }
})

onUnmounted(() => {
  if (previewTimer) window.clearTimeout(previewTimer)
})
</script>

<style scoped lang="scss">
.selection-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.92);
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
    max-width: 720px;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.last-updated {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.42);
}

.card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
}

.workspace-card {
  margin-bottom: 20px;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 2.2fr 1fr 2fr auto;
  gap: 12px;
  align-items: end;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;

  span {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.58);
  }

  input,
  select {
    width: 100%;
    min-height: 40px;
    padding: 0 12px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    background: rgba(255, 255, 255, 0.04);
    color: rgba(255, 255, 255, 0.9);
  }
}

.toolbar-actions,
.header-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.workspace-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}

.meta-chip,
.status-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: rgba(255, 255, 255, 0.74);
}

.guide-chip {
  color: rgba(255, 255, 255, 0.88);
}

.status-chip.accent {
  color: #8fb7ff;
}

.selection-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  gap: 20px;
  align-items: start;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    font-size: 20px;
    color: rgba(255, 255, 255, 0.92);
  }

  p {
    margin: 6px 0 0;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.54);
    line-height: 1.5;
  }
}

.empty-state {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  border: 1px dashed rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.56);

  h4 {
    margin: 0;
    color: rgba(255, 255, 255, 0.9);
    font-size: 18px;
  }

  p {
    margin: 0;
    font-size: 13px;
  }
}

.results-table-wrapper {
  overflow: auto;
}

.results-table {
  width: 100%;
  border-collapse: collapse;

  th,
  td {
    padding: 12px 14px;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    vertical-align: middle;
  }

  th {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: rgba(255, 255, 255, 0.5);
  }

  td {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.86);
  }
}

.result-row {
  cursor: pointer;
  transition: background 0.2s ease;
}

.result-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.stock-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stock-code {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.48);
}

.signal-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;

  &.bullish {
    background: rgba(0, 200, 83, 0.14);
    color: #00c853;
  }

  &.bearish {
    background: rgba(255, 23, 68, 0.14);
    color: #ff6b88;
  }

  &.neutral {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.78);
  }
}

.change-cell.positive {
  color: #00c853;
}

.change-cell.negative {
  color: #ff6b88;
}

.score-cell {
  font-weight: 700;
  color: #8fb7ff;
}

.explanation-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.explanation-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 14px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-primary {
  background: #2962FF;
  color: #fff;

  &:hover:not(:disabled) {
    background: #1E53E5;
  }
}

.btn-secondary {
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.86);

  &:hover:not(:disabled) {
    border-color: rgba(41, 98, 255, 0.28);
    background: rgba(41, 98, 255, 0.08);
  }
}

.btn-danger {
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 23, 68, 0.08);
  color: #ff9bb0;

  &:hover:not(:disabled) {
    border-color: rgba(255, 23, 68, 0.28);
    background: rgba(255, 23, 68, 0.14);
  }
}

@media (max-width: 1200px) {
  .selection-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .page-header,
  .card-header {
    flex-direction: column;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }
}
</style>
