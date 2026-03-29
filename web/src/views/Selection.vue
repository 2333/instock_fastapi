<template>
  <div class="selection-page">
    <div class="page-header">
      <div class="header-left">
        <h1>股票精选</h1>
        <p class="subtitle">运行规范筛选并进入个股验证详情</p>
      </div>
      <div class="header-right">
        <button class="btn btn-secondary" @click="toggleCriteriaPanel">
          {{ criteriaCollapsed ? '展开条件' : '收起条件' }}
        </button>
        <button class="btn btn-secondary" @click="saveCriteria">保存条件</button>
        <button class="btn btn-primary" @click="runSelection" :disabled="loading">
          {{ loading ? '运行中...' : '开始筛选' }}
        </button>
      </div>
    </div>

    <div class="selection-layout">
      <aside
        v-show="!criteriaCollapsed"
        ref="criteriaPanelRef"
        class="criteria-panel"
        :style="{ width: `${criteriaPanelWidth}px` }"
      >
        <div class="panel-section">
          <h3>价格条件</h3>
          <div class="criteria-group">
            <label>价格范围</label>
            <div class="range-inputs">
              <input type="number" v-model.number="criteria.priceMin" placeholder="最小" class="input-small">
              <span>-</span>
              <input type="number" v-model.number="criteria.priceMax" placeholder="最大" class="input-small">
            </div>
          </div>
          <div class="criteria-group">
            <label>市值 (亿元)</label>
            <div class="range-inputs">
              <input type="number" v-model.number="criteria.marketCapMin" placeholder="最小" class="input-small">
              <span>-</span>
              <input type="number" v-model.number="criteria.marketCapMax" placeholder="最大" class="input-small">
            </div>
          </div>
        </div>

        <div class="panel-section">
          <h3>涨跌幅条件</h3>
          <div class="criteria-group">
            <label>日涨跌 (%)</label>
            <div class="range-inputs">
              <input type="number" v-model.number="criteria.changeMin" placeholder="最小" class="input-small">
              <span>-</span>
              <input type="number" v-model.number="criteria.changeMax" placeholder="最大" class="input-small">
            </div>
          </div>
          <div class="criteria-group">
            <label>周涨跌 (%)</label>
            <div class="range-inputs">
              <input type="number" v-model.number="criteria.weekChangeMin" placeholder="最小" class="input-small">
              <span>-</span>
              <input type="number" v-model.number="criteria.weekChangeMax" placeholder="最大" class="input-small">
            </div>
          </div>
        </div>

        <div class="panel-section">
          <h3>技术指标</h3>
          <div class="criteria-group">
            <label>市盈率</label>
            <div class="range-inputs">
              <input type="number" v-model.number="criteria.peMin" placeholder="最小" class="input-small">
              <span>-</span>
              <input type="number" v-model.number="criteria.peMax" placeholder="最大" class="input-small">
            </div>
          </div>
          <div class="criteria-group">
            <label>RSI (14)</label>
            <div class="range-inputs">
              <input type="number" v-model.number="criteria.rsiMin" placeholder="最小" class="input-small">
              <span>-</span>
              <input type="number" v-model.number="criteria.rsiMax" placeholder="最大" class="input-small">
            </div>
          </div>
          <div class="criteria-group">
            <label>MACD 信号</label>
            <div class="checkbox-group">
              <label class="checkbox-item">
                <input type="checkbox" v-model="criteria.macdBullish">
                <span>MACD 看涨</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="criteria.macdBearish">
                <span>MACD 看跌</span>
              </label>
            </div>
          </div>
        </div>

        <div class="panel-section">
          <h3>成交量条件</h3>
          <div class="criteria-group">
            <label>量比</label>
            <div class="range-inputs">
              <input type="number" v-model.number="criteria.volumeRatioMin" placeholder="最小" class="input-small">
              <span>-</span>
              <input type="number" v-model.number="criteria.volumeRatioMax" placeholder="最大" class="input-small">
            </div>
          </div>
        </div>
      </aside>

      <div
        v-show="!criteriaCollapsed"
        class="panel-resizer"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整筛选条件宽度"
        @mousedown="startCriteriaResize"
        @touchstart.prevent="startCriteriaResize"
      ></div>

      <main class="results-panel">
        <div class="review-note">
          <strong>Milestone 3</strong>
          <span>当前前端已接入规范筛选结果与个股验证链路，规范接口支持价格、日涨跌幅、市场三个筛选维度。</span>
        </div>

        <div v-if="!hasResults" class="empty-state">
          <div class="empty-icon">🎯</div>
          <h3>暂无结果</h3>
          <p>运行筛选后可查看命中原因，并进入个股详情复核验证数据</p>
        </div>

        <template v-else>
          <div class="results-header">
            <div class="results-summary">
              <span class="results-count">共 {{ screeningSummary.total }} 只股票</span>
              <span v-if="screeningSummary.tradeDate" class="results-date">
                筛选交易日 {{ formatDisplayDate(screeningSummary.tradeDate) }}
              </span>
            </div>
            <div class="results-actions">
              <select v-model="sortBy" class="filter-select">
                <option value="score">按评分排序</option>
                <option value="date">按日期排序</option>
              </select>
            </div>
          </div>

          <div class="results-table-wrapper">
            <table class="results-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th>评分</th>
                  <th>命中原因</th>
                  <th>验证入口</th>
                  <th>日期</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="stock in sortedResults" 
                  :key="stock.code"
                  @click="openStockDetail(stock)"
                >
                  <td class="stock-code">{{ stock.code }}</td>
                  <td class="stock-name">{{ stock.name || '-' }}</td>
                  <td>{{ stock.score }}</td>
                  <td class="reason-cell">
                    <div class="reason-summary">{{ stock.reason_summary || '已命中筛选条件' }}</div>
                    <div v-if="stock.evidence.length" class="evidence-list">
                      <span
                        v-for="item in stock.evidence.slice(0, 3)"
                        :key="`${stock.code}-${item.key}`"
                        class="evidence-chip"
                      >
                        {{ formatEvidence(item) }}
                      </span>
                    </div>
                  </td>
                  <td>
                    <button class="detail-link" @click.stop="openStockDetail(stock)">
                      查看验证
                    </button>
                  </td>
                  <td>{{ stock.date || stock.trade_date }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { selectionApi } from '@/api'
import { useResizablePanel } from '@/composables/useResizablePanel'

interface ScreeningEvidenceItem {
  key: string
  label: string
  value: string | number | boolean | null
  operator?: string | null
  condition?: string | number | boolean | null
  matched?: boolean
}

interface StockResult {
  ts_code: string
  code: string
  stock_name: string
  name?: string
  score: number
  signal: string
  trade_date: string
  date?: string
  reason_summary?: string | null
  evidence: ScreeningEvidenceItem[]
}

const router = useRouter()
const loading = ref(false)
const hasResults = ref(false)
const results = ref<StockResult[]>([])
const sortBy = ref('score')
const screeningSummary = ref({
  total: 0,
  tradeDate: '',
})
const criteriaPanelRef = ref<HTMLElement | null>(null)
const criteriaCollapsed = ref(false)
const CRITERIA_WIDTH_KEY = 'instock_selection_panel_width'
const CRITERIA_COLLAPSED_KEY = 'instock_selection_panel_collapsed'
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')
const { panelWidth: criteriaPanelWidth, hydrateWidth: hydrateCriteriaWidth, startResize: startCriteriaResize } = useResizablePanel({
  panelRef: criteriaPanelRef,
  storageKey: CRITERIA_WIDTH_KEY,
  defaultWidth: 360,
  minWidth: 300,
  maxWidth: 520,
})

const criteria = reactive({
  priceMin: null as number | null,
  priceMax: null as number | null,
  market: '' as '' | 'sh' | 'sz',
  changeMin: null as number | null,
  changeMax: null as number | null,
  marketCapMin: null as number | null,
  marketCapMax: null as number | null,
  weekChangeMin: null as number | null,
  weekChangeMax: null as number | null,
  peMin: null as number | null,
  peMax: null as number | null,
  rsiMin: null as number | null,
  rsiMax: null as number | null,
  macdBullish: false,
  macdBearish: false,
  volumeRatioMin: null as number | null,
  volumeRatioMax: null as number | null,
})
const CRITERIA_STORAGE_KEY = 'instock_selection_criteria'

const canonicalFilterKeys = ['priceMin', 'priceMax', 'changeMin', 'changeMax', 'market'] as const
const nonCanonicalLabels: Record<string, string> = {
  marketCapMin: '市值下限',
  marketCapMax: '市值上限',
  weekChangeMin: '周涨跌下限',
  weekChangeMax: '周涨跌上限',
  peMin: '市盈率下限',
  peMax: '市盈率上限',
  rsiMin: 'RSI 下限',
  rsiMax: 'RSI 上限',
  macdBullish: 'MACD 看涨',
  macdBearish: 'MACD 看跌',
  volumeRatioMin: '量比下限',
  volumeRatioMax: '量比上限',
}

const sortedResults = computed(() => {
  const sorted = [...results.value]
  sorted.sort((a, b) => {
    switch (sortBy.value) {
      case 'score': return Number(b.score) - Number(a.score)
      case 'date': return (b.date || b.trade_date || '').localeCompare(a.date || a.trade_date || '')
      default: return Number(b.score) - Number(a.score)
    }
  })
  return sorted
})

const formatDisplayDate = (value?: string | null) => {
  if (!value) return '-'
  if (value.includes('-')) return value
  if (value.length !== 8) return value
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
}

const normalizeResult = (item: any): StockResult => ({
  ...item,
  code: item.code || item.symbol || item.ts_code?.split('.')[0],
  name: item.stock_name || item.name,
  evidence: Array.isArray(item.evidence) ? item.evidence : [],
})

const buildCanonicalFilters = () => {
  return canonicalFilterKeys.reduce<Record<string, unknown>>((acc, key) => {
    const value = criteria[key]
    if (value !== null && value !== '') {
      acc[key] = value
    }
    return acc
  }, {})
}

const getIgnoredCriteriaLabels = () => {
  return Object.entries(nonCanonicalLabels)
    .filter(([key]) => {
      const value = criteria[key as keyof typeof criteria]
      return value !== null && value !== '' && value !== false
    })
    .map(([, label]) => label)
}

const formatEvidence = (item: ScreeningEvidenceItem) => {
  const operator = item.operator ? ` ${item.operator} ${item.condition}` : ''
  const value = item.value ?? '-'
  return `${item.label}: ${value}${operator}`
}

const openStockDetail = (stock: StockResult) => {
  router.push({
    path: `/stock/${stock.code}`,
    query: {
      screening_date: stock.trade_date || stock.date || '',
    },
  })
}

const fetchResults = async () => {
  loading.value = true
  try {
    const response = await selectionApi.getScreeningHistory({ limit: 100 })
    const payload = response?.data || {}
    results.value = (payload.items || []).map(normalizeResult)
    screeningSummary.value = {
      total: Number(payload.total || results.value.length),
      tradeDate: payload.trade_date || results.value[0]?.trade_date || '',
    }
    hasResults.value = results.value.length > 0
  } catch (e) {
    console.error('Failed to fetch selection results:', e)
    results.value = []
    screeningSummary.value = { total: 0, tradeDate: '' }
  } finally {
    loading.value = false
  }
}

const runSelection = async () => {
  loading.value = true
  try {
    const ignoredCriteria = getIgnoredCriteriaLabels()
    if (ignoredCriteria.length > 0) {
      showNotification?.('warning', `本次规范筛选暂未接入：${ignoredCriteria.join('、')}`)
    }

    const response = await selectionApi.runScreening({
      filters: buildCanonicalFilters(),
      scope: {
        limit: 100,
        market: criteria.market || undefined,
      },
    })
    const payload = response?.data || {}
    results.value = (payload.items || []).map(normalizeResult)
    screeningSummary.value = {
      total: Number(payload.total || results.value.length),
      tradeDate: payload.query?.trade_date || results.value[0]?.trade_date || '',
    }
    hasResults.value = results.value.length > 0
    showNotification?.('success', `筛选完成，共 ${results.value.length} 只`)
  } catch (e) {
    console.error('Failed to run selection:', e)
    showNotification?.('error', '执行筛选失败')
  } finally {
    loading.value = false
  }
}

const saveCriteria = () => {
  window.localStorage.setItem(CRITERIA_STORAGE_KEY, JSON.stringify(criteria))
  showNotification?.('success', '筛选条件已保存')
}

const toggleCriteriaPanel = () => {
  criteriaCollapsed.value = !criteriaCollapsed.value
  window.localStorage.setItem(CRITERIA_COLLAPSED_KEY, criteriaCollapsed.value ? '1' : '0')
}

onMounted(() => {
  const savedCriteria = window.localStorage.getItem(CRITERIA_STORAGE_KEY)
  if (savedCriteria) {
    try {
      Object.assign(criteria, JSON.parse(savedCriteria))
    } catch {
      // ignore broken local cache
    }
  }
  hydrateCriteriaWidth()
  criteriaCollapsed.value = window.localStorage.getItem(CRITERIA_COLLAPSED_KEY) === '1'
  fetchResults()
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
  margin-bottom: 24px;

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.header-right {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;

  &.btn-primary {
    background: #2962FF;
    color: white;

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  &.btn-secondary {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);
  }

  &.btn-small {
    padding: 6px 12px;
    font-size: 12px;
  }
}

.selection-layout {
  display: flex;
  gap: 12px;
}

.criteria-panel {
  min-width: 280px;
  max-width: 600px;
  flex-shrink: 0;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  max-height: calc(100vh - 140px);
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

.panel-resizer {
  position: relative;
  flex: 0 0 12px;
  margin: 0 -6px;
  cursor: col-resize;
  touch-action: none;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
  }

  &::after {
    content: '';
    position: absolute;
    top: 16px;
    bottom: 16px;
    left: 50%;
    width: 2px;
    transform: translateX(-50%);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
    transition: background 0.2s ease;
  }

  &:hover::after {
    background: rgba(41, 98, 255, 0.75);
  }
}

.panel-section {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }

  h3 {
    margin: 0 0 16px;
    font-size: 14px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
  }
}

.criteria-group {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }

  label {
    display: block;
    margin-bottom: 8px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.range-inputs {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.input-small {
  min-width: 0;
  width: 100%;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  min-width: 0;

  input {
    accent-color: #2962FF;
  }

  span {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
    overflow-wrap: anywhere;
  }
}

.results-panel {
  flex: 1;
  min-width: 0;
}

.review-note {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px 14px;
  background: rgba(41, 98, 255, 0.08);
  border: 1px solid rgba(41, 98, 255, 0.2);
  border-radius: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.72);

  strong {
    color: #9ab7ff;
  }
}

@media (max-width: 1200px) {
  .selection-layout {
    flex-direction: column;
    gap: 24px;
  }

  .criteria-panel {
    width: 100%;
    min-width: 0;
    max-width: none;
    max-height: 50vh;
  }

  .panel-resizer {
    display: none;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  text-align: center;

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  h3 {
    margin: 0 0 8px;
    font-size: 20px;
  }

  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.5);
  }
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.results-count {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.results-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.results-date {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.results-actions {
  display: flex;
  gap: 12px;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(26, 26, 26, 0.5);
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

.results-table-wrapper {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.results-table {
  width: 100%;
  border-collapse: collapse;

  th,
  td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  th {
    background: rgba(26, 26, 26, 0.95);
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
  }

  td {
    font-size: 13px;
  }

  tbody tr {
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.03);
    }
  }
}

.stock-code {
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.stock-name {
  color: rgba(255, 255, 255, 0.7);
}

.reason-cell {
  min-width: 280px;
}

.reason-summary {
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.84);
  line-height: 1.4;
}

.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.evidence-chip {
  display: inline-flex;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.58);
  font-size: 11px;
}

.detail-link {
  padding: 6px 10px;
  border: 1px solid rgba(41, 98, 255, 0.35);
  border-radius: 999px;
  background: rgba(41, 98, 255, 0.1);
  color: #9ab7ff;
  font-size: 12px;
  cursor: pointer;
}

.macd-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;

  &.bullish {
    background: rgba(0, 200, 83, 0.15);
    color: #00C853;
  }

  &.bearish {
    background: rgba(255, 23, 68, 0.15);
    color: #FF1744;
  }
}
</style>
