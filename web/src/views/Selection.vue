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
        <button class="btn btn-secondary" @click="saveCurrentStrategy" :disabled="savingStrategy">
          {{ savingStrategy ? '保存中...' : '保存为策略' }}
        </button>
        <button
          class="btn btn-primary"
          @click="saveStrategyAndGoBacktest"
          :disabled="savingStrategy || !hasResults"
        >
          {{ savingStrategy ? '保存中...' : '保存并去回测' }}
        </button>
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
        <div v-if="!templatesCollapsed" class="panel-section templates-section">
          <div class="section-heading">
            <h3>快捷模板</h3>
            <p class="section-hint">一键应用常用筛选组合</p>
          </div>
          <div v-if="templatesLoading" class="templates-loading">加载中...</div>
          <div v-else class="templates-grid">
            <button
              v-for="tpl in templates"
              :key="tpl.id"
              class="template-card"
              @click="applyTemplate(tpl)"
            >
              <span class="template-icon">{{ tpl.icon }}</span>
              <span class="template-name">{{ tpl.name }}</span>
              <span class="template-desc">{{ tpl.description }}</span>
            </button>
          </div>
          <button class="templates-toggle" @click="templatesCollapsed = true">收起模板</button>
        </div>

        <div v-if="recentTemplates.length && !templatesCollapsed" class="panel-section recent-templates-section">
          <div class="section-heading">
            <h3>最近使用</h3>
            <p class="section-hint">快速重新应用最近使用的模板</p>
          </div>
          <div class="recent-templates-grid">
            <button
              v-for="tpl in recentTemplates"
              :key="tpl.id"
              class="template-card recent-template-card"
              @click="applyTemplate(tpl)"
            >
              <span class="template-icon">{{ tpl.icon }}</span>
              <span class="template-name">{{ tpl.name }}</span>
            </button>
          </div>
        </div>

        <div v-else class="templates-collapsed-bar">
          <button class="btn btn-small" @click="templatesCollapsed = false">展开快捷模板</button>
        </div>
        <div class="panel-section">
          <div class="section-heading">
            <h3>当前可用筛选</h3>
            <p>规范筛选接口当前支持价格、日涨跌幅和市场范围。</p>
          </div>
          <div class="criteria-group">
            <label>市场范围</label>
            <select v-model="criteria.market" class="filter-select criteria-select">
              <option value="">全部市场</option>
              <option
                v-for="option in marketOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="myConditions.length" class="panel-section saved-conditions-section">
          <div class="section-heading">
            <h3>已保存条件</h3>
            <p class="section-hint">点击加载到面板</p>
          </div>
          <div class="saved-conditions-list">
            <button
              v-for="cond in myConditions"
              :key="cond.id"
              class="saved-condition-item"
              @click="loadSavedCondition(cond)"
            >
              <span class="saved-condition-name">{{ cond.name }}</span>
              <span :class="['saved-condition-category', categoryClass(cond.category)]">
                {{ cond.category }}
              </span>
            </button>
          </div>
        </div>

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
        </div>

        <div class="panel-section">
          <div class="section-heading">
            <h3>技术指标</h3>
            <p>基于最新交易日的技术指标进行筛选。</p>
          </div>

          <div class="criteria-group">
            <label>RSI 范围</label>
            <div class="range-inputs">
              <input type="number" v-model.number="criteria.rsiMin" placeholder="最小" min="0" max="100" class="input-small">
              <span>-</span>
              <input type="number" v-model.number="criteria.rsiMax" placeholder="最大" min="0" max="100" class="input-small">
            </div>
            <p class="field-hint">RSI 相对强弱指标，通常 0-100，超卖区域低于 30</p>
          </div>

          <div class="criteria-group">
            <label>MACD 信号</label>
            <div class="checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="criteria.macdBullish">
                只看 MACD 看涨（金叉倾向）
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="criteria.macdBearish">
                只看 MACD 看跌（死叉倾向）
              </label>
            </div>
            <p class="field-hint">MACD 柱状图是否为正（看涨）或为负（看跌）</p>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-heading">
            <h3>形态条件</h3>
            <p>把 K 线形态纳入筛选，和价格、涨跌幅、指标一起组合使用。</p>
          </div>
          <div class="criteria-group">
            <label>形态</label>
            <select v-model="criteria.pattern" class="filter-select criteria-select">
              <option value="">不限形态</option>
              <option v-for="pattern in patternOptions" :key="pattern.value" :value="pattern.value">
                {{ pattern.label }}
              </option>
            </select>
            <p class="field-hint">命中后会写入结果证据，例如锤子线、头肩底、双底等。</p>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-heading">
            <h3>其他条件</h3>
            <p>以下条件暂未接入，不会参与当前筛选。</p>
          </div>
          <div class="legacy-grid">
            <section
              v-for="group in unavailableFilterGroups"
              :key="group.title"
              class="legacy-card"
            >
              <h4>{{ group.title }}</h4>
              <ul class="legacy-list">
                <li v-for="item in group.items" :key="item">{{ item }}</li>
              </ul>
            </section>
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
        <div class="availability-note">
          <strong>规范筛选说明</strong>
          <span>{{ supportedFiltersDescription }}</span>
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
              <button
                v-if="!compareMode"
                class="btn btn-secondary"
                @click="enableCompareMode"
              >
                对比结果
              </button>
              <button
                v-else
                class="btn btn-primary"
                :disabled="selectedHistoryIds.size < 2"
                @click="startCompare"
              >
                对比选中 ({{ selectedHistoryIds.size }})
              </button>
              <button
                v-if="compareMode"
                class="btn btn-secondary"
                @click="exitCompareMode"
              >
                取消
              </button>
            </div>
          </div>

          <div class="results-table-wrapper">
            <table class="results-table">
              <thead>
                <tr>
                  <th v-if="compareMode" style="width: 48px;">
                    <input
                      type="checkbox"
                      :checked="allCurrentSelectionIdsSelected"
                      @change="toggleSelectAll"
                      title="全选"
                    />
                  </th>
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
                  :class="{ 'row-selected': compareMode && selectedHistoryIds.has(extractSelectionId(stock)) }"
                  @click="compareMode ? handleRowClick(stock) : openStockDetail(stock)"
                >
                  <td v-if="compareMode" @click.stop>
                    <input
                      type="checkbox"
                      :checked="selectedHistoryIds.has(extractSelectionId(stock))"
                      @change="toggleSelection(extractSelectionId(stock))"
                    />
                  </td>
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
                    <button class="watchlist-link" @click.stop="addToWatchlist(stock.code)">
                      加入关注
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

  <!-- Comparison Modal -->
  <div v-if="showCompareModal" class="modal-overlay" @click.self="showCompareModal = false">
    <div class="modal-content comparison-modal">
      <div class="modal-header">
        <h3>对比结果 ({{ comparisonResults.length }} 个筛选)</h3>
        <button class="close-btn" @click="showCompareModal = false">×</button>
      </div>
      <div class="modal-body">
        <div v-if="comparisonResults.length === 0" class="empty-state">
          无数据
        </div>
        <div v-else class="comparison-grid">
          <div
            v-for="item in comparisonResults"
            :key="item.history_id"
            class="comparison-card"
          >
            <div class="card-header">
              <div class="card-title">筛选 {{ item.history_id.slice(-8) }}</div>
              <div class="card-subtitle">{{ formatDisplayDate(item.trade_date) }}</div>
            </div>
            <div class="card-stats">
              <div class="stat">
                <span class="stat-label">股票数</span>
                <span class="stat-value">{{ item.total }}</span>
              </div>
              <div class="stat">
                <span class="stat-label">平均分</span>
                <span class="stat-value">{{ item.avg_score?.toFixed(2) }}</span>
              </div>
            </div>
            <div class="card-top-stocks">
              <h4>Top 5</h4>
              <ul>
                <li v-for="stock in item.top_stocks" :key="stock.code">
                  <span class="stock-code">{{ stock.code }}</span>
                  <span class="stock-name">{{ stock.name }}</span>
                  <span class="stock-score">{{ stock.score?.toFixed(2) }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { attentionApi, selectionApi, strategyApi } from '@/api'
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

interface FilterMetadataItem {
  key: string
  label: string
  value_type: string
  operators: string[]
}

const router = useRouter()
const loading = ref(false)
const hasResults = ref(false)
const results = ref<StockResult[]>([])
const sortBy = ref('score')
const screeningMetadata = ref<{
  filter_fields?: FilterMetadataItem[]
  markets?: string[]
} | null>(null)
const screeningSummary = ref({
  total: 0,
  tradeDate: '',
})
const criteriaPanelRef = ref<HTMLElement | null>(null)
const criteriaCollapsed = ref(false)
const myConditions = ref<Array<{ id: number; name: string; category: string; params: Record<string, any> }>>([])
const templates = ref<Array<{ id: string; name: string; description: string; icon: string; filters: Record<string, any> }>>([])
const templatesLoading = ref(false)
const templatesCollapsed = ref(false)
const recentTemplates = ref<Array<{ id: string; name: string; icon: string; filters: Record<string, any> }>>([])
const savingStrategy = ref(false)
// Comparison mode state
const compareMode = ref(false)
const selectedHistoryIds = ref<Set<string>>(new Set())
const showCompareModal = ref(false)
const comparisonResults = ref<Array<{
  history_id: string
  trade_date: string | null
  total: number
  avg_score: number | null
  top_stocks: StockResult[]
}>>([])
const CRITERIA_WIDTH_KEY = 'instock_selection_panel_width'
const CRITERIA_COLLAPSED_KEY = 'instock_selection_panel_collapsed'
const TEMPLATES_COLLAPSED_KEY = 'instock_templates_collapsed'
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
  pattern: '' as string,
  volumeRatioMin: null as number | null,
  volumeRatioMax: null as number | null,
})

const canonicalFilterKeys = [
  'priceMin', 'priceMax',
  'changeMin', 'changeMax',
  'market',
  'rsiMin', 'rsiMax',
  'macdBullish', 'macdBearish',
  'pattern',
] as const
const defaultSupportedFilterLabels = ['价格范围', '日涨跌幅', '市场范围', 'RSI', 'MACD', '形态']
const marketLabelMap: Record<string, string> = {
  sh: '沪市',
  sz: '深市',
}
const patternOptions = [
  { label: '锤子线', value: 'HAMMER' },
  { label: '倒锤子线', value: 'INVERTED_HAMMER' },
  { label: '十字星', value: 'DOJI' },
  { label: '看涨吞没', value: 'BULLISH_ENGULFING' },
  { label: '看跌吞没', value: 'BEARISH_ENGULFING' },
  { label: '看涨孕线', value: 'BULLISH_HARAMI' },
  { label: '看跌孕线', value: 'BEARISH_HARAMI' },
  { label: '头肩底', value: 'INVERSE_HEAD_SHOULDERS' },
  { label: '头肩顶', value: 'HEAD_SHOULDERS' },
  { label: '双底', value: 'DOUBLE_BOTTOM' },
  { label: '双顶', value: 'DOUBLE_TOP' },
  { label: 'MA 金叉', value: 'MA_GOLDEN_CROSS' },
  { label: 'MA 死叉', value: 'MA_DEATH_CROSS' },
]
const unavailableFilterGroups = [
  { title: '价格扩展', items: ['市值范围'] },
  { title: '涨跌扩展', items: ['周涨跌幅'] },
  { title: '技术指标扩展', items: ['市盈率', 'KDJ', 'BOLL'] },
  { title: '成交量', items: ['量比'] },
]

const marketOptions = computed(() => {
  const metadataMarkets = screeningMetadata.value?.markets || []
  const normalized = metadataMarkets
    .map((label) => {
      const value = Object.entries(marketLabelMap).find(([, name]) => name === label)?.[0]
      return value ? { value, label } : null
    })
    .filter((item): item is { value: 'sh' | 'sz'; label: string } => item !== null)

  return normalized.length > 0
    ? normalized
    : [
        { value: 'sh' as const, label: '沪市' },
        { value: 'sz' as const, label: '深市' },
    ]
})

const supportedFiltersDescription = computed(() => {
  const labels = screeningMetadata.value?.filter_fields?.length
    ? Array.from(
        new Set(
          screeningMetadata.value.filter_fields.map((item) => {
            if (item.key.startsWith('price')) return '价格范围'
            if (item.key.startsWith('change')) return '日涨跌幅'
            if (item.key === 'market') return '市场范围'
            if (item.key.startsWith('rsi')) return 'RSI'
            if (item.key.startsWith('macd')) return 'MACD'
            if (item.key === 'pattern') return '形态'
            return item.label
          })
        )
      )
    : defaultSupportedFilterLabels

  return `当前启用：${labels.join('、')}。其他条件暂未接入。`
})

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

const getTopBacktestStockCode = () => {
  const topStock = sortedResults.value.find((stock) => String(stock.code || '').trim())
  return String(topStock?.code || '').trim()
}

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

const buildSelectionStrategyParams = () => {
  const selectionFilters = buildCanonicalFilters()
  const selectionScope = {
    market: criteria.market || undefined,
    limit: 100,
  }

  return {
    source: 'selection',
    template_name: 'selection_bridge',
    selection_filters: selectionFilters,
    selection_scope: selectionScope,
    entry_rules: {
      mode: 'screening_match',
      inherits: ['selection_filters', 'selection_scope'],
      filters: selectionFilters,
      scope: selectionScope,
    },
    exit_rules: {
      mode: 'configurable',
      rules: [
        { name: 'take_profit_pct', label: '止盈百分比', type: 'number' },
        { name: 'stop_loss_pct', label: '止损百分比', type: 'number' },
        { name: 'max_hold_days', label: '最大持有天数', type: 'number' },
      ],
    },
    backtest_config: {},
    strategy_params: {},
  }
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

const addToWatchlist = async (code: string) => {
  if (!code) return
  try {
    await attentionApi.add(code, 'watch')
    showNotification?.('success', `已加入关注: ${code}`)
  } catch (e) {
    console.error('Failed to add to watchlist:', e)
    showNotification?.('error', '加入关注失败')
  }
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

const fetchScreeningMetadata = async () => {
  try {
    const response = await selectionApi.getScreeningMetadata()
    screeningMetadata.value = response?.data || null
  } catch (e) {
    console.error('Failed to fetch screening metadata:', e)
    screeningMetadata.value = null
  }
}

const runSelection = async () => {
  loading.value = true
  try {
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

const fetchMyConditions = async () => {
  try {
    const conditions = await selectionApi.getMyConditions()
    myConditions.value = Array.isArray(conditions) ? conditions : []
  } catch (e) {
    myConditions.value = []
  }
}

const fetchTemplates = async () => {
  templatesLoading.value = true
  try {
    const response = await selectionApi.getTemplates()
    templates.value = (response?.data || []).map((tpl: any) => ({
      ...tpl,
      filters: tpl.filters || {},
    }))
    // Load recent templates from localStorage
    const recentKey = 'selection_recent_templates'
    try {
      const stored = localStorage.getItem(recentKey)
      if (stored) {
        const recentIds = JSON.parse(stored) as string[]
        recentTemplates.value = templates.value.filter((tpl: any) => recentIds.includes(tpl.id))
      }
    } catch (e) {
      recentTemplates.value = []
    }
  } catch (e) {
    templates.value = []
    recentTemplates.value = []
  } finally {
    templatesLoading.value = false
  }
}

const applyTemplate = (tpl: { id: string; name: string; filters: Record<string, any> }) => {
  // Merge template filters into criteria, overriding existing values
  Object.assign(criteria, tpl.filters)
  showNotification?.('info', `已应用模板：${tpl.name}`)
  // Record to recent templates
  const recentKey = 'selection_recent_templates'
  try {
    const stored = localStorage.getItem(recentKey)
    const recentIds: string[] = stored ? JSON.parse(stored) : []
    const filtered = recentIds.filter((id) => id !== tpl.id)
    const updated = [tpl.id, ...filtered].slice(0, 5)
    localStorage.setItem(recentKey, JSON.stringify(updated))
    // Update local recentTemplates
    const tplData = templates.value.find((t: any) => t.id === tpl.id)
    if (tplData && !recentTemplates.value.find((t: any) => t.id === tpl.id)) {
      recentTemplates.value = [tplData, ...recentTemplates.value].slice(0, 5)
    }
  } catch (e) {
    // ignore
  }
}

const loadSavedCondition = (cond: { id: number; name: string; params: Record<string, any> }) => {
  // 加载参数到criteria
  const canonical = canonicalFilterKeys.reduce<Record<string, any>>((acc, key) => {
    if (cond.params && cond.params[key] !== undefined) {
      acc[key] = cond.params[key]
    } else {
      acc[key] = criteria[key] // keep current
    }
    return acc
  }, {})
  Object.assign(criteria, canonical)
  showNotification?.('info', `已加载条件：${cond.name}`)
}

const saveCriteria = async () => {
  const name = prompt("为筛选条件命名：", `自定义筛选 ${new Date().toLocaleDateString()}`)
  if (!name?.trim()) return

  try {
    await selectionApi.createCondition({
      name: name.trim(),
      category: "custom",
      description: "从筛选页面保存的条件",
      params: buildCanonicalFilters(),
      is_active: true,
    })
    showNotification?.('success', '筛选条件已保存')
    await fetchMyConditions()
  } catch (e) {
    showNotification?.('error', '保存失败')
  }
}

const saveAsStrategy = async (goToBacktest = false) => {
  const suggestedName = `筛选策略-${new Date().toLocaleDateString()}`
  const name = window.prompt('为策略命名：', suggestedName)
  if (!name?.trim()) return

  savingStrategy.value = true
  try {
    const created = await strategyApi.createMyStrategyFromSelection({
      name: name.trim(),
      description: '由筛选条件生成的策略模板',
      params: buildSelectionStrategyParams(),
      is_active: true,
    })
    const savedStrategyId = String(created?.id || '')
    if (goToBacktest && savedStrategyId) {
      const stockCode = getTopBacktestStockCode()
      if (!stockCode) {
        showNotification?.('warning', '当前没有可带入回测的股票结果，请先运行筛选')
        return
      }
      await router.push({
        path: '/backtest',
        query: {
          saved: savedStrategyId,
          stock: stockCode,
        },
      })
      showNotification?.('success', `策略已保存，已带着当前结果 Top1(${stockCode}) 进入回测页`)
      return
    }
    showNotification?.('success', '策略已保存，筛选到策略的桥接配置已建立')
  } catch (e) {
    console.error('Failed to save strategy from selection:', e)
    showNotification?.('error', '保存策略失败')
  } finally {
    savingStrategy.value = false
  }
}

const saveCurrentStrategy = () => {
  void saveAsStrategy(false)
}

const saveStrategyAndGoBacktest = () => {
  void saveAsStrategy(true)
}

// Comparison functionality
const extractSelectionId = (stock: any): string => {
  return stock.selection_id || stock.selectionId || ''
}

const enableCompareMode = () => {
  compareMode.value = true
  selectedHistoryIds.value = new Set()
}

const exitCompareMode = () => {
  compareMode.value = false
  selectedHistoryIds.value = new Set()
}

const toggleSelection = (selId: string) => {
  const newSet = new Set(selectedHistoryIds.value)
  if (newSet.has(selId)) {
    newSet.delete(selId)
  } else if (newSet.size < 4) {
    newSet.add(selId)
  }
  selectedHistoryIds.value = newSet
}

const toggleSelectAll = () => {
  const allIds = Array.from(new Set(results.value.map(extractSelectionId)))
  if (allCurrentSelectionIdsSelected.value) {
    selectedHistoryIds.value = new Set()
  } else {
    // Select up to 4
    selectedHistoryIds.value = new Set(allIds.slice(0, 4))
  }
}

const allCurrentSelectionIdsSelected = computed(() => {
  const uniqueIds = new Set(results.value.map(extractSelectionId))
  if (uniqueIds.size === 0) return false
  return uniqueIds.size > 0 && Array.from(uniqueIds).every(id => selectedHistoryIds.value.has(id))
})

const handleRowClick = (stock: any) => {
  const selId = extractSelectionId(stock)
  if (!selId) return
  toggleSelection(selId)
}

const startCompare = async () => {
  if (selectedHistoryIds.value.size < 2) return
  try {
    const response = await selectionApi.compareScreeningResults(Array.from(selectedHistoryIds.value))
    comparisonResults.value = (response?.data || []).map((item: any) => ({
      ...item,
      top_stocks: (item.top_stocks || []).map((s: any) => ({
        ...s,
        code: s.code || s.ts_code?.split('.')[0],
        name: s.stock_name,
      })),
    }))
    showCompareModal.value = true
  } catch (e) {
    console.error('Comparison failed:', e)
    showNotification?.('error', '对比失败')
  }
}

const toggleCriteriaPanel = () => {
  criteriaCollapsed.value = !criteriaCollapsed.value
  window.localStorage.setItem(CRITERIA_COLLAPSED_KEY, criteriaCollapsed.value ? '1' : '0')
}

const categoryClass = (category: string | null | undefined): string => {
  const c = String(category || '').toLowerCase()
  if (c.includes('price') || c.includes('价格')) return 'category-price'
  if (c.includes('change') || c.includes('涨跌')) return 'category-change'
  if (c.includes('macd')) return 'category-macd'
  if (c.includes('rsi')) return 'category-rsi'
  if (c.includes('pattern') || c.includes('形态')) return 'category-pattern'
  if (c.includes('fund') || c.includes('资金')) return 'category-fund'
  return 'category-default'
}

onMounted(async () => {
  await Promise.all([
    fetchMyConditions(),
    fetchScreeningMetadata(),
    fetchResults(),
    fetchTemplates(),
  ])
  hydrateCriteriaWidth()
  criteriaCollapsed.value = window.localStorage.getItem(CRITERIA_COLLAPSED_KEY) === '1'
  templatesCollapsed.value = window.localStorage.getItem(TEMPLATES_COLLAPSED_KEY) === '1'
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

.templates-section {
  background: rgba(41, 98, 255, 0.06);
  border: 1px solid rgba(41, 98, 255, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;

  .templates-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 12px;
  }

  .template-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(41, 98, 255, 0.15);
      border-color: rgba(41, 98, 255, 0.35);
    }

    .template-icon {
      font-size: 20px;
      margin-bottom: 2px;
    }

    .template-name {
      font-size: 13px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
    }

    .template-desc {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      line-height: 1.4;
    }
  }

  .templates-loading {
    text-align: center;
    padding: 24px;
    color: rgba(255, 255, 255, 0.5);
    font-size: 13px;
  }

  .templates-toggle {
    width: 100%;
    padding: 8px;
    background: transparent;
    border: 1px dashed rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    color: rgba(255, 255, 255, 0.5);
    font-size: 12px;
    cursor: pointer;

    &:hover {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.3);
    }
  }
}

.templates-collapsed-bar {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(41, 98, 255, 0.06);
  border: 1px solid rgba(41, 98, 255, 0.15);
  border-radius: 12px;
  text-align: center;
}

.recent-templates-section {
  background: rgba(255, 152, 0, 0.06);
  border: 1px solid rgba(255, 152, 0, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;

  .recent-templates-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .recent-template-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);

    &:hover {
      background: rgba(255, 152, 0, 0.12);
      border-color: rgba(255, 152, 0, 0.3);
    }
  }
}

.section-heading {
  margin-bottom: 16px;

  h3 {
    margin-bottom: 6px;
  }

  p {
    margin: 0;
    font-size: 12px;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.5);
  }
}

.saved-conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.saved-condition-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.12);
  }

  .saved-condition-name {
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
  }

  .saved-condition-category {
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;

    &.category-price { background: rgba(41, 98, 255, 0.15); color: #7aa7ff; border: 1px solid rgba(41, 98, 255, 0.3); }
    &.category-change { background: rgba(255, 152, 0, 0.15); color: #FFB74D; border: 1px solid rgba(255, 152, 0, 0.3); }
    &.category-macd { background: rgba(139, 195, 74, 0.15); color: #AED581; border: 1px solid rgba(139, 195, 74, 0.3); }
    &.category-rsi { background: rgba(233, 30, 99, 0.15); color: #F06292; border: 1px solid rgba(233, 30, 99, 0.3); }
    &.category-pattern { background: rgba(156, 39, 176, 0.15); color: #BA68C8; border: 1px solid rgba(156, 39, 176, 0.3); }
    &.category-fund { background: rgba(0, 188, 212, 0.15); color: #4DD0E1; border: 1px solid rgba(0, 188, 212, 0.3); }
    &.category-default { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.6); border: 1px solid rgba(255, 255, 255, 0.2); }
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

.criteria-select {
  width: 100%;
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

.legacy-grid {
  display: grid;
  gap: 12px;
}

.legacy-card {
  padding: 14px;
  border: 1px dashed rgba(255, 255, 255, 0.14);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);

  h4 {
    margin: 0 0 10px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.72);
  }
}

.legacy-list {
  margin: 0;
  padding-left: 18px;
  color: rgba(255, 255, 255, 0.48);
  font-size: 12px;
  line-height: 1.6;
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

.availability-note {
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
  margin-right: 6px;
}

.watchlist-link {
  padding: 6px 10px;
  border: 1px solid rgba(0, 200, 83, 0.35);
  border-radius: 999px;
  background: rgba(0, 200, 83, 0.1);
  color: #69F0AE;
  font-size: 12px;
  cursor: pointer;

  &:hover {
    background: rgba(0, 200, 83, 0.2);
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

// Comparison modal styles
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.modal-content {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  max-width: 1200px;
  width: 100%;
  max-height: 90vh;
  overflow: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 28px;
    color: rgba(255, 255, 255, 0.5);
    cursor: pointer;
    line-height: 1;

    &:hover {
      color: rgba(255, 255, 255, 0.9);
    }
  }
}

.modal-body {
  padding: 24px;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.comparison-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
}

.card-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  .card-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .card-subtitle {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.card-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;

  .stat {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .stat-label {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
    }

    .stat-value {
      font-size: 20px;
      font-weight: 600;
      color: #2962FF;
    }
  }
}

.card-top-stocks {
  h4 {
    margin: 0 0 10px;
    font-size: 13px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  li {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 8px;

    .stock-code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
    }

    .stock-name {
      flex: 1;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.7);
    }

    .stock-score {
      font-size: 13px;
      font-weight: 600;
      color: #9ab7ff;
    }
  }
}

// Row selection style
.row-selected {
  background: rgba(41, 98, 255, 0.12) !important;
}

.results-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

</style>
