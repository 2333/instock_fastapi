<template>
  <div class="selection-page">
    <div class="page-header">
      <div class="header-left">
        <h1>股票精选</h1>
        <p class="subtitle">根据条件筛选和选择股票</p>
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

      <main class="results-panel">
        <div v-if="!hasResults" class="empty-state">
          <div class="empty-icon">🎯</div>
          <h3>暂无结果</h3>
          <p>配置筛选条件后点击"开始筛选"</p>
        </div>

        <template v-else>
          <div class="results-header">
            <span class="results-count">共 {{ results.length }} 只股票</span>
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
                  <th>信号</th>
                  <th>日期</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="stock in sortedResults" 
                  :key="stock.code"
                  @click="$router.push(`/stock/${stock.code}`)"
                >
                  <td class="stock-code">{{ stock.code }}</td>
                  <td class="stock-name">{{ stock.name || '-' }}</td>
                  <td>{{ stock.score }}</td>
                  <td>
                    <span class="signal-badge" :class="stock.signal">{{ stock.signal }}</span>
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
import { ref, reactive, computed, onMounted, onBeforeUnmount, inject } from 'vue'
import { selectionApi } from '@/api'

interface StockResult {
  ts_code: string
  code: string
  stock_name: string
  score: number
  signal: string
  trade_date: string
}

const loading = ref(false)
const hasResults = ref(false)
const results = ref<StockResult[]>([])
const sortBy = ref('score')
const criteriaPanelRef = ref<HTMLElement | null>(null)
const criteriaPanelWidth = ref(360)
const criteriaCollapsed = ref(false)
const CRITERIA_WIDTH_KEY = 'instock_selection_panel_width'
const CRITERIA_COLLAPSED_KEY = 'instock_selection_panel_collapsed'
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')

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

const fetchResults = async () => {
  loading.value = true
  try {
    const data = await selectionApi.getHistory({ limit: 100 })
    results.value = (data || []).map((r: any) => ({
      ...r,
      code: r.code || r.symbol || r.ts_code?.split('.')[0],
      name: r.stock_name || r.name,
    }))
    hasResults.value = results.value.length > 0
  } catch (e) {
    console.error('Failed to fetch selection results:', e)
    results.value = []
  } finally {
    loading.value = false
  }
}

const runSelection = async () => {
  loading.value = true
  try {
    const data = await selectionApi.runSelection(criteria)
    results.value = (data || []).map((r: any) => ({
      ...r,
      code: r.code || r.symbol || r.ts_code?.split('.')[0],
      name: r.stock_name || r.name,
    }))
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

const persistCriteriaWidth = () => {
  if (!criteriaPanelRef.value) return
  const width = Math.round(criteriaPanelRef.value.getBoundingClientRect().width)
  if (width >= 300 && width <= 520) {
    criteriaPanelWidth.value = width
    window.localStorage.setItem(CRITERIA_WIDTH_KEY, String(width))
  }
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
  const savedWidth = Number(window.localStorage.getItem(CRITERIA_WIDTH_KEY) || 0)
  if (savedWidth >= 300 && savedWidth <= 520) {
    criteriaPanelWidth.value = savedWidth
  }
  criteriaCollapsed.value = window.localStorage.getItem(CRITERIA_COLLAPSED_KEY) === '1'
  window.addEventListener('mouseup', persistCriteriaWidth)
  window.addEventListener('touchend', persistCriteriaWidth)
  fetchResults()
})

onBeforeUnmount(() => {
  window.removeEventListener('mouseup', persistCriteriaWidth)
  window.removeEventListener('touchend', persistCriteriaWidth)
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
  gap: 24px;
}

.criteria-panel {
  width: clamp(300px, 24vw, 500px);
  min-width: 300px;
  max-width: 520px;
  flex-shrink: 0;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  max-height: calc(100vh - 180px);
  overflow-y: auto;
  resize: horizontal;
  overflow-x: hidden;
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-small {
  flex: 1;
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

  input {
    accent-color: #2962FF;
  }

  span {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
  }
}

.results-panel {
  flex: 1;
  min-width: 0;
}

@media (max-width: 1200px) {
  .selection-layout {
    flex-direction: column;
  }

  .criteria-panel {
    width: 100%;
    min-width: 0;
    max-width: none;
    resize: none;
    max-height: none;
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

.signal-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;

  &.buy {
    background: rgba(0, 200, 83, 0.15);
    color: #00C853;
  }

  &.sell {
    background: rgba(255, 23, 68, 0.15);
    color: #FF1744;
  }

  &.hold {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.6);
  }
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
