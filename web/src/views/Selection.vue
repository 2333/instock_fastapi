<template>
  <div class="selection-studio">
    <header class="studio-header">
      <div>
        <p class="eyebrow">Selection Studio</p>
        <h1>组合选股</h1>
        <p class="subtitle">用规则树组合技术指标、基本面和形态条件，统一周期做实时筛选。</p>
      </div>
      <div class="header-actions">
        <select v-model="selectedPresetId" class="pill-select" @change="handlePresetChange">
          <option value="">当前未绑定方案</option>
          <option v-for="preset in presets" :key="preset.id" :value="String(preset.id)">
            {{ preset.name }}
          </option>
        </select>
        <select v-model="period" class="pill-select" @change="schedulePreview">
          <option v-for="periodItem in catalog?.periods || []" :key="periodItem.key" :value="periodItem.key">
            {{ periodItem.label }}
          </option>
        </select>
        <button class="ghost-btn" @click="resetTemplate">新方案</button>
        <button class="ghost-btn" @click="savePreset(false)">保存</button>
        <button class="ghost-btn" @click="savePreset(true)">另存为</button>
        <button class="ghost-btn danger" :disabled="!selectedPresetId" @click="deletePreset">删除</button>
        <button class="primary-btn" :disabled="running" @click="runSelection(true)">
          {{ running ? '筛选中...' : '立即筛选' }}
        </button>
      </div>
    </header>

    <section class="template-bar">
      <label>
        <span>方案名称</span>
        <input v-model.trim="presetName" type="text" placeholder="例如：日线趋势突破" />
      </label>
      <div class="summary-chips">
        <span v-for="group in catalog?.groups || []" :key="group.key" class="summary-chip">
          {{ group.label }} {{ group.items.length }}
        </span>
      </div>
    </section>

    <div class="studio-layout">
      <section class="builder-panel">
        <div class="panel-header">
          <div>
            <h2>规则树</h2>
            <p>每个条件都可以配置参数、左右值比较和时序包装；组之间支持 AND / OR / NOT。</p>
          </div>
          <div class="panel-actions">
            <span class="status-pill">周期：{{ periodLabel }}</span>
            <span class="status-pill">条件：{{ totalConditions }}</span>
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

      <aside class="results-panel">
        <div class="panel-header compact">
          <div>
            <h2>结果</h2>
            <p v-if="resultMeta.trade_date">{{ resultMeta.trade_date }} · {{ periodLabel }} · 共 {{ results.length }} 只</p>
            <p v-else>配置条件后点击“立即筛选”，或保存时自动预览。</p>
          </div>
          <div class="panel-actions">
            <span class="status-pill">{{ running ? '实时刷新中' : '已同步' }}</span>
          </div>
        </div>

        <div v-if="!results.length" class="empty-state">
          <div class="empty-mark">RULES</div>
          <h3>当前没有命中结果</h3>
          <p>先在左侧规则树里添加条件，或加载一个已有方案。</p>
        </div>

        <div v-else class="results-list">
          <article v-for="item in results" :key="item.ts_code" class="result-card" @click="$router.push(`/stock/${item.code}`)">
            <div class="result-top">
              <div>
                <p class="result-code">{{ item.code }}</p>
                <h3>{{ item.stock_name }}</h3>
              </div>
              <div class="result-score">
                <span>Score</span>
                <strong>{{ item.score.toFixed(2) }}</strong>
              </div>
            </div>

            <div class="result-metrics">
              <span>{{ item.signal }}</span>
              <span>收盘 {{ formatNumber(item.snapshot?.close) }}</span>
              <span>涨跌 {{ formatSigned(item.snapshot?.pct_chg) }}%</span>
              <span>{{ item.matched_conditions || 0 }}/{{ item.total_conditions || 0 }} 条命中</span>
            </div>

            <div class="result-explanations">
              <p v-for="explanation in item.explanations?.slice(0, 2) || []" :key="explanation.id">
                <strong>{{ explanation.label || explanation.metric_key }}</strong>
                <span>{{ operatorLabels[explanation.operator] || explanation.operator }}</span>
                <span>{{ formatScalar(explanation.match_left) }}</span>
                <span>{{ formatScalar(explanation.match_right) }}</span>
              </p>
            </div>
          </article>
        </div>
      </aside>
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
    label: '主规则',
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
      description: `规则树方案 · ${periodLabel.value}`,
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
    label: '子规则',
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
.selection-studio {
  --panel-bg: rgba(12, 15, 19, 0.92);
  --panel-border: rgba(255, 255, 255, 0.08);
  --text-muted: rgba(255, 255, 255, 0.58);
  padding: 24px;
}

.studio-header,
.panel-header,
.template-bar {
  border: 1px solid var(--panel-border);
  background: radial-gradient(circle at top left, rgba(73, 156, 255, 0.16), transparent 34%), linear-gradient(180deg, rgba(17, 20, 25, 0.98), rgba(11, 14, 18, 0.98));
  border-radius: 24px;
  padding: 20px 22px;
}

.studio-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.42);
}

h1,
h2,
h3 {
  margin: 0;
  color: rgba(255, 255, 255, 0.95);
}

.subtitle,
.panel-header p,
.template-bar span,
.result-explanations p {
  color: var(--text-muted);
}

.subtitle {
  margin: 10px 0 0;
  max-width: 720px;
  line-height: 1.6;
}

.header-actions,
.panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-start;
  justify-content: flex-end;
}

.pill-select,
.template-bar input,
.ghost-btn,
.primary-btn {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.92);
  padding: 10px 14px;
}

.primary-btn {
  background: linear-gradient(135deg, #58a9ff, #8ed5ff);
  color: #081018;
  border-color: transparent;
  cursor: pointer;
  font-weight: 700;
}

.ghost-btn {
  cursor: pointer;
}

.ghost-btn.danger {
  color: #ffb7b7;
}

.template-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.template-bar label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 260px;
  color: rgba(255, 255, 255, 0.62);
}

.summary-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.summary-chip,
.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13px;
}

.studio-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.9fr);
  gap: 16px;
  align-items: start;
}

.builder-panel,
.results-panel {
  border: 1px solid var(--panel-border);
  border-radius: 24px;
  padding: 20px;
  background: var(--panel-bg);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.panel-header.compact {
  padding: 0;
  background: transparent;
  border: none;
}

.panel-header p {
  margin: 8px 0 0;
  line-height: 1.5;
}

.empty-state {
  min-height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 10px;
  border: 1px dashed rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  color: var(--text-muted);
}

.empty-mark {
  font-size: 12px;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: rgba(120, 197, 255, 0.62);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: calc(100vh - 250px);
  overflow-y: auto;
  padding-right: 4px;
}

.result-card {
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease;
}

.result-card:hover {
  transform: translateY(-1px);
  border-color: rgba(88, 169, 255, 0.42);
}

.result-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.result-code {
  margin: 0 0 4px;
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.46);
}

.result-top h3 {
  font-size: 18px;
}

.result-score {
  text-align: right;
}

.result-score span {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.48);
}

.result-score strong {
  font-size: 28px;
  color: #93d8ff;
}

.result-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.result-metrics span {
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.74);
  font-size: 12px;
}

.result-explanations {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-explanations p {
  margin: 0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
  line-height: 1.5;
}

.result-explanations strong {
  color: rgba(255, 255, 255, 0.9);
}

@media (max-width: 1180px) {
  .studio-layout {
    grid-template-columns: 1fr;
  }

  .results-list {
    max-height: none;
  }
}

@media (max-width: 860px) {
  .studio-header,
  .template-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions,
  .summary-chips {
    justify-content: flex-start;
  }
}
</style>
