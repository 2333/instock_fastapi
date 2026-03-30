<template>
  <div class="backtest-page">
    <div class="page-header">
      <div class="header-left">
        <h1>策略回测</h1>
        <p class="subtitle">测试和优化您的交易策略</p>
        <div v-if="currentBacktestId" class="backtest-id-hint">
          <span>结果编号：{{ currentBacktestId }}</span>
          <button class="backtest-id-copy" @click="copyBacktestId">复制编号</button>
        </div>
      </div>
      <div class="header-right">
        <button class="btn btn-secondary" @click="toggleConfigPanel">
          {{ configCollapsed ? '展开条件' : '收起条件' }}
        </button>
        <button class="btn btn-secondary" @click="loadTemplate">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          加载模板
        </button>
        <button class="btn btn-secondary" @click="saveStrategy" :disabled="loading || !selectedStrategyTemplate">
          保存策略
        </button>
        <button class="btn btn-secondary" @click="copyShareLink">
          复制链接
        </button>
        <button class="btn btn-primary" @click="runBacktest" :disabled="loading">
          <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          <span v-if="loading" class="spinner-small"></span>
          {{ loading ? '运行中...' : '运行回测' }}
        </button>
      </div>
    </div>

    <div class="backtest-layout">
      <aside
        v-show="!configCollapsed"
        ref="configPanelRef"
        class="config-panel"
        :style="{ width: `${configPanelWidth}px` }"
      >
        <div class="config-section">
          <h4>已保存配置</h4>
          <div class="config-row">
            <div class="config-item">
              <label>策略配置</label>
              <select v-model="selectedSavedStrategyId" class="select-full">
                <option value="">选择已保存策略</option>
                <option
                  v-for="strategy in savedStrategies"
                  :key="strategy.id"
                  :value="String(strategy.id)"
                >
                  {{ strategy.name }}
                </option>
              </select>
            </div>
            <div class="config-item config-action">
              <button
                class="btn btn-secondary btn-full"
                @click="applySavedStrategy"
                :disabled="!selectedSavedStrategy"
              >
                加载配置
              </button>
            </div>
          </div>
          <div class="config-row">
            <div class="config-item">
              <label>回测编号</label>
              <input v-model="currentBacktestId" type="text" class="input-text" placeholder="输入 bt 编号后加载">
            </div>
            <div class="config-item config-action">
              <button class="btn btn-secondary btn-full" @click="loadBacktestResult(currentBacktestId)" :disabled="!currentBacktestId">
                加载结果
              </button>
            </div>
          </div>
          <div v-if="backtestHistory.length" class="history-backtests">
            <div class="recent-backtests__head">
              <span class="recent-backtests__label">回测历史</span>
            </div>
            <div class="config-row history-filter-row">
              <div class="config-item">
                <input
                  v-model="historyFilter"
                  type="text"
                  class="input-text history-filter"
                  placeholder="按代码 / 策略 / 名称筛选"
                >
              </div>
              <div class="config-item">
                <select v-model="historySort" class="select-full history-sort">
                  <option value="created">按创建时间</option>
                  <option value="return">按总收益</option>
                  <option value="drawdown">按最大回撤</option>
                </select>
              </div>
            </div>
            <button
              v-for="item in filteredBacktestHistory"
              :key="item.id"
              class="history-backtests__item"
              @click="loadBacktestResult(item.id)"
            >
              <div class="history-backtests__top">
                <strong>{{ item.code || item.name }}</strong>
                <span :class="item.totalReturn !== null && item.totalReturn >= 0 ? 'price-up' : 'price-down'">
                  {{ formatPercent(item.totalReturn) }}
                </span>
              </div>
              <div class="history-backtests__meta">
                <span>{{ item.stockName || item.strategy || item.name }}</span>
                <span>{{ item.startDate }}-{{ item.endDate }}</span>
              </div>
              <div class="history-backtests__stats">
                <span>回撤 {{ formatPercent(item.maxDrawdown) }}</span>
                <span>创建 {{ formatDateTime(item.createdAt) }}</span>
              </div>
            </button>
          </div>

          <div v-if="recentBacktests.length" class="recent-backtests">
            <div class="recent-backtests__head">
              <span class="recent-backtests__label">最近查看</span>
              <button class="recent-backtests__clear" @click="clearRecentBacktests">清空</button>
            </div>
            <button
              v-for="backtestId in recentBacktests"
              :key="backtestId"
              class="recent-backtests__item"
              @click="loadBacktestResult(backtestId)"
            >
              #{{ backtestId }}
            </button>
          </div>
        </div>

        <div class="config-section">
          <h4>股票选择</h4>
          <div class="config-item">
            <label>股票代码</label>
            <input type="text" v-model="config.stockCode" placeholder="例如: 600519" class="input-text">
          </div>
          <div class="config-item">
            <label>数据周期</label>
            <select v-model="config.period" class="select-full">
              <option value="1y">最近1年</option>
              <option value="2y">最近2年</option>
              <option value="5y">最近5年</option>
              <option value="10y">最近10年</option>
            </select>
          </div>
        </div>

        <div class="config-section">
          <h4>资金与仓位</h4>
          <div class="config-row">
            <div class="config-item">
              <label>初始资金</label>
              <input type="number" v-model.number="config.initialCapital" class="input-number">
            </div>
            <div class="config-item">
              <label>仓位比例 (%)</label>
              <input type="number" v-model.number="config.positionSize" class="input-number">
            </div>
          </div>
          <div class="config-item">
            <label>最大仓位 (%)</label>
            <input type="number" v-model.number="config.maxPosition" class="input-number">
          </div>
        </div>

        <div class="config-section">
          <h4>风险管理</h4>
          <div class="config-row">
            <div class="config-item">
              <label>止损比例 (%)</label>
              <input type="number" v-model.number="config.stopLoss" class="input-number">
            </div>
            <div class="config-item">
              <label>止盈比例 (%)</label>
              <input type="number" v-model.number="config.takeProfit" class="input-number">
            </div>
          </div>
          <div class="config-item">
            <label>最低持仓天数</label>
            <input type="number" v-model.number="config.minHoldDays" class="input-number">
          </div>
        </div>

        <div class="config-section">
          <h4>交易成本</h4>
          <div class="config-row">
            <div class="config-item">
              <label>佣金比例 (%)</label>
              <input type="number" v-model.number="config.commissionRate" class="input-number" step="0.01">
            </div>
            <div class="config-item">
              <label>最低佣金</label>
              <input type="number" v-model.number="config.minCommission" class="input-number">
            </div>
          </div>
          <div class="config-item">
            <label>滑点比例 (%)</label>
            <input type="number" v-model.number="config.slippage" class="input-number" step="0.01">
          </div>
        </div>

        <div class="config-section">
          <h4>入场策略</h4>
          <div class="config-item">
            <label>策略类型</label>
            <select v-model="config.strategyType" class="select-full">
              <option
                v-for="template in strategyTemplates"
                :key="template.name"
                :value="template.name"
              >
                {{ template.displayName }}
              </option>
            </select>
          </div>
          <p v-if="selectedStrategyTemplate?.description" class="strategy-description">
            {{ selectedStrategyTemplate.description }}
          </p>
          <div
            v-if="selectedStrategyTemplate?.parameters.length"
            class="strategy-params"
          >
            <div class="config-row">
              <div
                v-for="param in selectedStrategyTemplate.parameters"
                :key="param.name"
                class="config-item"
              >
                <label>{{ param.label }}</label>
                <select
                  v-if="param.type === 'select'"
                  v-model="strategyParams[param.name]"
                  class="select-full"
                >
                  <option
                    v-for="option in param.options || []"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </option>
                </select>
                <input
                  v-else-if="param.type === 'number'"
                  v-model.number="strategyParams[param.name]"
                  class="input-number"
                  :min="param.min"
                  :max="param.max"
                  :step="param.step || 1"
                >
                <input
                  v-else
                  type="text"
                  v-model="strategyParams[param.name]"
                  class="input-text"
                >
              </div>
            </div>
          </div>
        </div>
      </aside>

      <div
        v-show="!configCollapsed"
        class="panel-resizer"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整条件面板宽度"
        @mousedown="startConfigResize"
        @touchstart.prevent="startConfigResize"
      ></div>

      <main class="results-panel">
        <div v-if="!hasResults" class="empty-state">
          <div class="empty-icon">📊</div>
          <h3>暂无回测结果</h3>
          <p>配置策略参数后点击"运行回测"查看结果</p>
        </div>

        <template v-else>
          <div class="card result-summary-card">
            <div class="card-header">
              <h3>结果摘要</h3>
              <span class="summary-badge" :class="resultSummaryTone">{{ resultSummaryTag }}</span>
            </div>
            <p class="result-summary-text">{{ resultSummaryText }}</p>

            <div v-if="compareRows.length" class="compare-grid">
              <div class="compare-row compare-row--head">
                <span>参数</span>
                <span>当前配置</span>
                <span>已保存配置</span>
              </div>
              <div v-for="row in compareRows" :key="row.label" class="compare-row">
                <span>{{ row.label }}</span>
                <strong>{{ row.current }}</strong>
                <strong>{{ row.saved }}</strong>
              </div>
            </div>

            <div v-if="resultCompareRows.length" class="compare-grid compare-grid--metrics">
              <div class="compare-row compare-row--head compare-row--delta">
                <span>结果</span>
                <span>当前回测</span>
                <span>历史记录</span>
                <span>变化</span>
              </div>
              <div v-for="row in resultCompareRows" :key="row.label" class="compare-row compare-row--delta">
                <span>{{ row.label }}</span>
                <strong>{{ row.current }}</strong>
                <strong>{{ row.saved }}</strong>
                <strong :class="row.deltaTone">{{ row.delta }}</strong>
              </div>
            </div>
          </div>

          <div class="metrics-grid">
            <div class="metric-card">
              <div class="metric-header">
                <span class="metric-label">总收益率</span>
                <span class="metric-badge" :class="metrics.totalReturn >= 0 ? 'bullish' : 'bearish'">
                  {{ metrics.totalReturn >= 0 ? '+' : '' }}{{ metrics.totalReturn.toFixed(2) }}%
                </span>
              </div>
              <div class="metric-value">{{ formatCurrency(metrics.finalCapital) }}</div>
              <div class="metric-detail">初始: {{ formatCurrency(metrics.initialCapital) }}</div>
            </div>

            <div class="metric-card">
              <div class="metric-header">
                <span class="metric-label">年化收益率</span>
              </div>
              <div class="metric-value" :class="metrics.annualizedReturn >= 0 ? 'price-up' : 'price-down'">
                {{ metrics.annualizedReturn >= 0 ? '+' : '' }}{{ metrics.annualizedReturn.toFixed(2) }}%
              </div>
            </div>

            <div class="metric-card">
              <div class="metric-header">
                <span class="metric-label">最大回撤</span>
              </div>
              <div class="metric-value price-down">{{ metrics.maxDrawdown.toFixed(2) }}%</div>
            </div>

            <div class="metric-card">
              <div class="metric-header">
                <span class="metric-label">夏普比率</span>
              </div>
              <div class="metric-value">{{ metrics.sharpeRatio.toFixed(2) }}</div>
            </div>

            <div class="metric-card">
              <div class="metric-header">
                <span class="metric-label">胜率</span>
              </div>
              <div class="metric-value price-up">{{ metrics.winRate.toFixed(1) }}%</div>
              <div class="metric-detail">{{ metrics.winningTrades }} / {{ metrics.totalTrades }} 笔交易</div>
            </div>

            <div class="metric-card">
              <div class="metric-header">
                <span class="metric-label">盈亏因子</span>
              </div>
              <div class="metric-value">{{ metrics.profitFactor.toFixed(2) }}</div>
            </div>
          </div>

          <div class="charts-row">
            <div class="card chart-card">
              <div class="card-header">
                <h3>权益曲线</h3>
                <div class="chart-legend">
                  <span class="legend-item">
                    <span class="legend-color equity"></span>
                    组合净值
                  </span>
                  <span class="legend-item">
                    <span class="legend-color benchmark"></span>
                    买入持有
                  </span>
                </div>
              </div>
              <div ref="equityChartRef" class="chart-wrapper"></div>
            </div>
          </div>

          <div class="trades-section">
            <div class="card">
              <div class="card-header">
                <h3>交易记录</h3>
                <div class="trade-stats">
                  <span class="stat-item">平均盈利: <strong class="price-up">{{ formatCurrency(metrics.avgWin) }}</strong></span>
                  <span class="stat-item">平均亏损: <strong class="price-down">{{ formatCurrency(metrics.avgLoss) }}</strong></span>
                </div>
              </div>
              <div class="trades-table-wrapper">
                <table class="trades-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>日期</th>
                      <th>类型</th>
                      <th>价格</th>
                      <th>数量</th>
                      <th>盈亏</th>
                      <th>收益率</th>
                      <th>持仓天数</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="trade in trades" 
                      :key="trade.id"
                      :class="trade.type.toLowerCase()"
                    >
                      <td>{{ trade.id }}</td>
                      <td>{{ trade.date }}</td>
                      <td>
                        <span class="trade-type" :class="trade.type.toLowerCase()">
                          {{ trade.type === 'BUY' ? '买入' : trade.type === 'SELL' ? '卖出' : trade.type }}
                        </span>
                      </td>
                      <td>{{ trade.price.toFixed(2) }}</td>
                      <td>{{ trade.quantity }}</td>
                      <td :class="trade.profit >= 0 ? 'price-up' : 'price-down'">
                        {{ trade.profit >= 0 ? '+' : '' }}{{ formatCurrency(trade.profit) }}
                      </td>
                      <td :class="trade.returnPct >= 0 ? 'price-up' : 'price-down'">
                        {{ trade.returnPct >= 0 ? '+' : '' }}{{ trade.returnPct.toFixed(2) }}%
                      </td>
                      <td>{{ trade.holdDays }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useResizeObserver } from '@vueuse/core'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { backtestApi, strategyApi } from '@/api'
import { useResizablePanel } from '@/composables/useResizablePanel'

echarts.use([
  LineChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
])

interface Trade {
  id: number
  date: string
  type: string
  price: number
  quantity: number
  profit: number
  returnPct: number
  holdDays: number
}

interface StrategyTemplateOption {
  label: string
  value: string
}

interface StrategyTemplateParam {
  name: string
  label: string
  type: string
  default: string | number | null
  min?: number
  max?: number
  step?: number
  options?: StrategyTemplateOption[]
}

interface StrategyTemplate {
  name: string
  displayName: string
  description?: string
  defaultParams: Record<string, string | number>
  parameters: StrategyTemplateParam[]
}

interface SavedStrategy {
  id: number
  name: string
  description?: string
  params?: Record<string, unknown>
  isActive: boolean
}

interface BacktestHistoryItem {
  id: string
  name: string
  startDate: string
  endDate: string
  initialCapital: number
  finalCapital: number | null
  totalReturn: number | null
  annualReturn: number | null
  maxDrawdown: number | null
  sharpeRatio: number | null
  winRate: number | null
  totalTrades: number | null
  code?: string
  stockName?: string
  strategy?: string
  createdAt?: string
}

const loading = ref(false)
const hasResults = ref(false)
const currentBacktestId = ref('')
const recentBacktests = ref<string[]>([])
const backtestHistory = ref<BacktestHistoryItem[]>([])
const historyFilter = ref('')
const historySort = ref<'created' | 'return' | 'drawdown'>('created')
const equityChartRef = ref<HTMLDivElement>()
const equityChartInstance = shallowRef<any>(null)
const equityCurve = ref<{ date: string; equity: number; benchmark: number }[]>([])
const strategyTemplates = ref<StrategyTemplate[]>([])
const savedStrategies = ref<SavedStrategy[]>([])
const selectedSavedStrategyId = ref('')
const configPanelRef = ref<HTMLElement | null>(null)
const configCollapsed = ref(false)
const PANEL_WIDTH_KEY = 'instock_backtest_panel_width'
const PANEL_COLLAPSED_KEY = 'instock_backtest_panel_collapsed'
const RECENT_BACKTESTS_KEY = 'instock_backtest_recent_ids'
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')
const route = useRoute()
const router = useRouter()
const { panelWidth: configPanelWidth, hydrateWidth: hydrateConfigWidth, startResize: startConfigResize } = useResizablePanel({
  panelRef: configPanelRef,
  storageKey: PANEL_WIDTH_KEY,
  defaultWidth: 380,
  minWidth: 320,
  maxWidth: 560,
})

const config = reactive({
  stockCode: '600519',
  period: '2y',
  initialCapital: 100000,
  positionSize: 10,
  maxPosition: 50,
  stopLoss: 5,
  takeProfit: 15,
  minHoldDays: 1,
  commissionRate: 0.03,
  minCommission: 5,
  slippage: 0.1,
  strategyType: 'ma_crossover',
})
const strategyParams = reactive<Record<string, string | number>>({})

const selectedStrategyTemplate = computed(() =>
  strategyTemplates.value.find((template) => template.name === config.strategyType) || null
)
const selectedSavedStrategy = computed(() =>
  savedStrategies.value.find((strategy) => String(strategy.id) === selectedSavedStrategyId.value) || null
)

const metrics = reactive({
  initialCapital: 100000,
  finalCapital: 100000,
  totalReturn: 0,
  annualizedReturn: 0,
  maxDrawdown: 0,
  sharpeRatio: 0,
  winRate: 0,
  totalTrades: 0,
  winningTrades: 0,
  profitFactor: 0,
  avgWin: 0,
  avgLoss: 0,
})

const trades = ref<Trade[]>([])

const resultSummaryTag = computed(() => {
  if (metrics.totalReturn > 0 && metrics.maxDrawdown > -10) return '表现稳健'
  if (metrics.totalReturn > 0) return '收益为正'
  if (metrics.totalReturn === 0) return '基本持平'
  return '需要复盘'
})

const resultSummaryTone = computed(() => {
  if (metrics.totalReturn > 0 && metrics.maxDrawdown > -10) return 'summary-badge--bullish'
  if (metrics.totalReturn > 0) return 'summary-badge--neutral'
  if (metrics.totalReturn === 0) return 'summary-badge--flat'
  return 'summary-badge--bearish'
})

const resultSummaryText = computed(() => {
  const returnPart = `区间总收益 ${metrics.totalReturn >= 0 ? '+' : ''}${metrics.totalReturn.toFixed(2)}%，最大回撤 ${metrics.maxDrawdown.toFixed(2)}%。`
  const tradePart = `共 ${metrics.totalTrades} 笔交易，胜率 ${metrics.winRate.toFixed(1)}%，夏普 ${metrics.sharpeRatio.toFixed(2)}。`

  if (metrics.totalReturn > 0 && metrics.maxDrawdown > -10) {
    return `${returnPart}${tradePart} 当前这组参数更接近“收益和回撤都可接受”的状态，可以作为后续对比基线。`
  }
  if (metrics.totalReturn > 0) {
    return `${returnPart}${tradePart} 收益已经转正，但回撤或波动仍值得继续优化。`
  }
  if (metrics.totalReturn === 0) {
    return `${returnPart}${tradePart} 当前结果接近持平，更适合继续调参或换模板验证。`
  }
  return `${returnPart}${tradePart} 当前参数组合没有形成理想结果，建议优先复盘模板与参数设置。`
})

const compareRows = computed(() => {
  if (!selectedSavedStrategy.value?.params) return []
  const saved = selectedSavedStrategy.value.params as Record<string, any>
  const savedParams = (saved.strategy_params && typeof saved.strategy_params === 'object') ? saved.strategy_params as Record<string, any> : {}

  return [
    { label: '股票', current: config.stockCode, saved: String(saved.stock_code || '--') },
    { label: '周期', current: config.period, saved: String(saved.period || '--') },
    { label: '模板', current: config.strategyType, saved: String(saved.strategy_type || saved.template || '--') },
    { label: '参数数量', current: String(Object.keys(strategyParams).length), saved: String(Object.keys(savedParams).length) },
  ]
})

const filteredBacktestHistory = computed(() => {
  const keyword = historyFilter.value.trim().toLowerCase()
  const filtered = !keyword
    ? [...backtestHistory.value]
    : backtestHistory.value.filter((item) =>
        [item.code, item.name, item.strategy, item.stockName].some((value) => String(value || '').toLowerCase().includes(keyword))
      )

  if (historySort.value === 'return') {
    return filtered.sort((a, b) => (b.totalReturn ?? -Infinity) - (a.totalReturn ?? -Infinity))
  }
  if (historySort.value === 'drawdown') {
    return filtered.sort((a, b) => (b.maxDrawdown ?? -Infinity) - (a.maxDrawdown ?? -Infinity))
  }
  return filtered.sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')))
})

const currentHistoryItem = computed(() =>
  backtestHistory.value.find((item) => item.id === currentBacktestId.value) || null
)

const formatDelta = (value: number | null | undefined, suffix = '') => {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}${suffix}`
}

const resultCompareRows = computed(() => {
  if (!currentHistoryItem.value) return []
  const totalReturnDelta = currentHistoryItem.value.totalReturn == null ? null : metrics.totalReturn - currentHistoryItem.value.totalReturn
  const drawdownDelta = currentHistoryItem.value.maxDrawdown == null ? null : metrics.maxDrawdown - currentHistoryItem.value.maxDrawdown
  const sharpeDelta = currentHistoryItem.value.sharpeRatio == null ? null : metrics.sharpeRatio - currentHistoryItem.value.sharpeRatio
  const tradeDelta = currentHistoryItem.value.totalTrades == null ? null : metrics.totalTrades - currentHistoryItem.value.totalTrades

  return [
    {
      label: '总收益',
      current: formatPercent(metrics.totalReturn),
      saved: formatPercent(currentHistoryItem.value.totalReturn),
      delta: formatDelta(totalReturnDelta, '%'),
      deltaTone: totalReturnDelta == null ? '' : totalReturnDelta >= 0 ? 'price-up' : 'price-down',
    },
    {
      label: '最大回撤',
      current: formatPercent(metrics.maxDrawdown),
      saved: formatPercent(currentHistoryItem.value.maxDrawdown),
      delta: formatDelta(drawdownDelta, '%'),
      deltaTone: drawdownDelta == null ? '' : drawdownDelta <= 0 ? 'price-up' : 'price-down',
    },
    {
      label: '夏普',
      current: metrics.sharpeRatio.toFixed(2),
      saved: currentHistoryItem.value.sharpeRatio == null ? '--' : currentHistoryItem.value.sharpeRatio.toFixed(2),
      delta: formatDelta(sharpeDelta),
      deltaTone: sharpeDelta == null ? '' : sharpeDelta >= 0 ? 'price-up' : 'price-down',
    },
    {
      label: '交易数',
      current: String(metrics.totalTrades),
      saved: currentHistoryItem.value.totalTrades == null ? '--' : String(currentHistoryItem.value.totalTrades),
      delta: tradeDelta == null ? '--' : `${tradeDelta > 0 ? '+' : ''}${tradeDelta}`,
      deltaTone: '',
    },
  ]
})

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)

const formatPercent = (value: number | null | undefined) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

const formatDate = (d: Date) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}${m}${day}`
}

const formatDateTime = (value?: string) => {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

const resolveDateRange = () => {
  const end = new Date()
  const start = new Date(end)
  if (config.period === '1y') start.setFullYear(start.getFullYear() - 1)
  if (config.period === '2y') start.setFullYear(start.getFullYear() - 2)
  if (config.period === '5y') start.setFullYear(start.getFullYear() - 5)
  if (config.period === '10y') start.setFullYear(start.getFullYear() - 10)
  return { start: formatDate(start), end: formatDate(end) }
}

const toggleConfigPanel = () => {
  configCollapsed.value = !configCollapsed.value
  window.localStorage.setItem(PANEL_COLLAPSED_KEY, configCollapsed.value ? '1' : '0')
}

const rememberBacktestId = (backtestId: string) => {
  const normalized = String(backtestId || '').trim()
  if (!normalized) return
  recentBacktests.value = [normalized, ...recentBacktests.value.filter((item) => item !== normalized)].slice(0, 6)
  window.localStorage.setItem(RECENT_BACKTESTS_KEY, JSON.stringify(recentBacktests.value))
}

const clearRecentBacktests = () => {
  recentBacktests.value = []
  window.localStorage.removeItem(RECENT_BACKTESTS_KEY)
  showNotification?.('info', '已清空最近查看记录')
}

const buildShareQuery = () => ({
  ...route.query,
  stock: config.stockCode || undefined,
  period: config.period || undefined,
  strategy: config.strategyType || undefined,
  saved: selectedSavedStrategyId.value || undefined,
  bt: currentBacktestId.value || undefined,
})

const syncQueryFromState = () => {
  void router.replace({
    query: buildShareQuery(),
  })
}

const copyShareLink = async () => {
  const href = router.resolve({ path: route.path, query: buildShareQuery() }).href
  const url = href.startsWith('http') ? href : `${window.location.origin}${href}`
  try {
    await navigator.clipboard.writeText(url)
    showNotification?.('success', '已复制当前回测链接')
  } catch (error) {
    showNotification?.('warning', '复制链接失败，请手动复制地址栏')
  }
}

const copyBacktestId = async () => {
  if (!currentBacktestId.value) return
  try {
    await navigator.clipboard.writeText(currentBacktestId.value)
    showNotification?.('success', '已复制回测编号')
  } catch (error) {
    showNotification?.('warning', '复制编号失败，请手动复制')
  }
}

const hydrateFromQuery = () => {
  const stock = typeof route.query.stock === 'string' ? route.query.stock : ''
  const period = typeof route.query.period === 'string' ? route.query.period : ''
  const strategy = typeof route.query.strategy === 'string' ? route.query.strategy : ''
  const saved = typeof route.query.saved === 'string' ? route.query.saved : ''
  const backtestId = typeof route.query.bt === 'string' ? route.query.bt : ''

  if (stock) config.stockCode = stock
  if (period) config.period = period
  if (strategy) config.strategyType = strategy
  if (saved) selectedSavedStrategyId.value = saved
  if (backtestId) currentBacktestId.value = backtestId
}

const normalizeTemplate = (template: any): StrategyTemplate => ({
  name: String(template?.name || ''),
  displayName: String(template?.display_name || template?.displayName || ''),
  description: template?.description ? String(template.description) : undefined,
  defaultParams: Object.fromEntries(
    Object.entries(template?.default_params || template?.defaultParams || {}).map(([key, value]) => [
      key,
      typeof value === 'number' || typeof value === 'string' ? value : String(value ?? ''),
    ])
  ),
  parameters: Array.isArray(template?.parameters)
    ? template.parameters.map((param: any) => ({
        name: String(param?.name || ''),
        label: String(param?.label || param?.name || ''),
        type: String(param?.type || 'number'),
        default:
          typeof param?.default === 'number' || typeof param?.default === 'string'
            ? param.default
            : null,
        min: typeof param?.min === 'number' ? param.min : undefined,
        max: typeof param?.max === 'number' ? param.max : undefined,
        step: typeof param?.step === 'number' ? param.step : undefined,
        options: Array.isArray(param?.options)
          ? param.options.map((option: any) => ({
              label: String(option?.label || option?.value || ''),
              value: String(option?.value || ''),
            }))
          : undefined,
      }))
    : [],
})

const normalizeSavedStrategy = (strategy: any): SavedStrategy => ({
  id: Number(strategy?.id || 0),
  name: String(strategy?.name || ''),
  description: strategy?.description ? String(strategy.description) : undefined,
  params: strategy?.params && typeof strategy.params === 'object' ? strategy.params : undefined,
  isActive: Boolean(strategy?.is_active ?? strategy?.isActive ?? true),
})

const normalizeBacktestHistoryItem = (item: any): BacktestHistoryItem => ({
  id: String(item?.id || ''),
  name: String(item?.name || ''),
  startDate: String(item?.start_date || item?.startDate || ''),
  endDate: String(item?.end_date || item?.endDate || ''),
  initialCapital: Number(item?.initial_capital ?? item?.initialCapital ?? 0),
  finalCapital:
    item?.final_capital === null || item?.final_capital === undefined
      ? null
      : Number(item.final_capital),
  totalReturn:
    item?.total_return === null || item?.total_return === undefined ? null : Number(item.total_return),
  annualReturn:
    item?.annual_return === null || item?.annual_return === undefined
      ? null
      : Number(item.annual_return),
  maxDrawdown:
    item?.max_drawdown === null || item?.max_drawdown === undefined
      ? null
      : Number(item.max_drawdown),
  sharpeRatio:
    item?.sharpe_ratio === null || item?.sharpe_ratio === undefined
      ? null
      : Number(item.sharpe_ratio),
  winRate: item?.win_rate === null || item?.win_rate === undefined ? null : Number(item.win_rate),
  totalTrades:
    item?.total_trades === null || item?.total_trades === undefined ? null : Number(item.total_trades),
  code: item?.code ? String(item.code) : undefined,
  stockName: item?.stock_name ? String(item.stock_name) : undefined,
  strategy: item?.strategy ? String(item.strategy) : undefined,
  createdAt: item?.created_at ? String(item.created_at) : undefined,
})

const applyTemplateDefaults = (template: StrategyTemplate | null) => {
  Object.keys(strategyParams).forEach((key) => {
    delete strategyParams[key]
  })
  if (!template) return

  Object.entries(template.defaultParams).forEach(([key, value]) => {
    strategyParams[key] = value
  })
}

const assignStrategyParams = (params: Record<string, unknown> | null | undefined) => {
  Object.keys(strategyParams).forEach((key) => {
    delete strategyParams[key]
  })
  Object.entries(params || {}).forEach(([key, value]) => {
    if (typeof value === 'number' || typeof value === 'string') {
      strategyParams[key] = value
    }
  })
}

const pickSavedValue = (saved: Record<string, unknown>, ...keys: string[]) =>
  keys.find((key) => saved[key] !== undefined) ? saved[keys.find((key) => saved[key] !== undefined) as string] : undefined

const applySavedStrategyParams = (params: Record<string, unknown> | null | undefined) => {
  const saved = params || {}
  const savedTemplate = String(
    saved.strategy_type || saved.template || (saved.strategy as Record<string, unknown> | undefined)?.template || ''
  ).trim()

  if (savedTemplate && strategyTemplates.value.some((template) => template.name === savedTemplate)) {
    config.strategyType = savedTemplate
  }

  const stockCode = pickSavedValue(saved, 'stock_code', 'stockCode')
  const period = pickSavedValue(saved, 'period')
  const initialCapital = pickSavedValue(saved, 'initial_capital', 'initialCapital')
  const positionSize = pickSavedValue(saved, 'position_size', 'positionSize')
  const maxPosition = pickSavedValue(saved, 'max_position', 'maxPosition')
  const stopLoss = pickSavedValue(saved, 'stop_loss', 'stopLoss')
  const takeProfit = pickSavedValue(saved, 'take_profit', 'takeProfit')
  const minHoldDays = pickSavedValue(saved, 'min_hold_days', 'minHoldDays')
  const commissionRate = pickSavedValue(saved, 'commission_rate', 'commissionRate')
  const minCommission = pickSavedValue(saved, 'min_commission', 'minCommission')
  const slippage = pickSavedValue(saved, 'slippage')

  if (stockCode !== undefined) {
    config.stockCode = String(stockCode).trim() || config.stockCode
  }
  if (period !== undefined) {
    config.period = String(period)
  }
  if (initialCapital !== undefined) {
    config.initialCapital = Number(initialCapital)
  }
  if (positionSize !== undefined) {
    config.positionSize = Number(positionSize)
  }
  if (maxPosition !== undefined) {
    config.maxPosition = Number(maxPosition)
  }
  if (stopLoss !== undefined) {
    config.stopLoss = Number(stopLoss)
  }
  if (takeProfit !== undefined) {
    config.takeProfit = Number(takeProfit)
  }
  if (minHoldDays !== undefined) {
    config.minHoldDays = Number(minHoldDays)
  }
  if (commissionRate !== undefined) {
    config.commissionRate = Number(commissionRate)
  }
  if (minCommission !== undefined) {
    config.minCommission = Number(minCommission)
  }
  if (slippage !== undefined) {
    config.slippage = Number(slippage)
  }

  const nestedStrategy = saved.strategy
  const nestedParams = nestedStrategy && typeof nestedStrategy === 'object'
    ? (nestedStrategy as Record<string, unknown>).params
    : undefined
  const flatParams = saved.strategy_params
  assignStrategyParams(
    flatParams && typeof flatParams === 'object'
      ? flatParams as Record<string, unknown>
      : nestedParams && typeof nestedParams === 'object'
        ? nestedParams as Record<string, unknown>
        : selectedStrategyTemplate.value?.defaultParams || {}
  )
}

const loadTemplate = () => {
  configCollapsed.value = false
  window.localStorage.setItem(PANEL_COLLAPSED_KEY, '0')
  applyTemplateDefaults(selectedStrategyTemplate.value)
  if (selectedStrategyTemplate.value) {
    showNotification?.('success', `已加载 ${selectedStrategyTemplate.value.displayName} 模板`)
  }
}

const loadSavedStrategies = async () => {
  try {
    const strategies = await strategyApi.getMyStrategies()
    savedStrategies.value = Array.isArray(strategies) ? strategies.map(normalizeSavedStrategy) : []
    if (selectedSavedStrategyId.value && selectedSavedStrategy.value) {
      applySavedStrategyParams(selectedSavedStrategy.value.params)
    }
  } catch (error) {
    savedStrategies.value = []
    showNotification?.('warning', '已保存策略加载失败')
  }
}

const loadBacktestHistory = async () => {
  try {
    const response = await backtestApi.getBacktestHistory(8)
    const items: any[] = Array.isArray(response?.data)
      ? response.data
      : Array.isArray(response)
        ? response
        : []
    backtestHistory.value = items
      .map(normalizeBacktestHistoryItem)
      .filter((item: BacktestHistoryItem) => item.id)
  } catch (error) {
    backtestHistory.value = []
    showNotification?.('warning', '回测历史加载失败')
  }
}

const loadStrategyTemplates = async () => {
  try {
    const templates = await strategyApi.getTemplates()
    strategyTemplates.value = Array.isArray(templates) ? templates.map(normalizeTemplate) : []
    if (!strategyTemplates.value.length) return

    if (!strategyTemplates.value.some((template) => template.name === config.strategyType)) {
      config.strategyType = strategyTemplates.value[0].name
    } else {
      applyTemplateDefaults(selectedStrategyTemplate.value)
    }
  } catch (error) {
    showNotification?.('warning', '策略模板加载失败，使用默认配置')
  }
}

const saveStrategy = async () => {
  if (!selectedStrategyTemplate.value) return

  try {
    const suggestedName = `${selectedStrategyTemplate.value.displayName}-${config.stockCode}`
    const strategyName = window.prompt('输入策略配置名称', suggestedName)?.trim()
    if (!strategyName) return

    const created = await strategyApi.createMyStrategy({
      name: strategyName,
      description: `从回测页保存：${selectedStrategyTemplate.value.displayName}`,
      params: {
        strategy_type: config.strategyType,
        stock_code: config.stockCode,
        period: config.period,
        initial_capital: config.initialCapital,
        position_size: config.positionSize,
        max_position: config.maxPosition,
        stop_loss: config.stopLoss,
        take_profit: config.takeProfit,
        min_hold_days: config.minHoldDays,
        commission_rate: config.commissionRate,
        min_commission: config.minCommission,
        slippage: config.slippage,
        strategy_params: { ...strategyParams },
      },
      is_active: true,
    })
    const normalized = normalizeSavedStrategy(created)
    savedStrategies.value = [normalized, ...savedStrategies.value.filter((item) => item.id !== normalized.id)]
    selectedSavedStrategyId.value = String(normalized.id)
    showNotification?.('success', '已保存当前策略配置')
  } catch (error) {
    showNotification?.('error', '保存策略失败')
  }
}

const applySavedStrategy = () => {
  if (!selectedSavedStrategy.value) return

  configCollapsed.value = false
  window.localStorage.setItem(PANEL_COLLAPSED_KEY, '0')
  applySavedStrategyParams(selectedSavedStrategy.value.params)
  showNotification?.('success', `已加载配置：${selectedSavedStrategy.value.name}`)
}

const applyBacktestResult = (result: any) => {
  const summary = result?.summary || result?.data?.result_data?.summary || {}
  const row = result?.data || {}
  metrics.initialCapital = Number(summary.initial_capital ?? row.initial_capital ?? config.initialCapital)
  metrics.finalCapital = Number(summary.final_capital ?? row.final_capital ?? config.initialCapital)
  metrics.totalReturn = Number(summary.total_return ?? row.total_return ?? 0)
  metrics.annualizedReturn = Number(summary.annual_return ?? row.annual_return ?? 0)
  metrics.maxDrawdown = Number(summary.max_drawdown ?? row.max_drawdown ?? 0)
  metrics.sharpeRatio = Number(summary.sharpe_ratio ?? row.sharpe_ratio ?? 0)
  metrics.winRate = Number(summary.win_rate ?? row.win_rate ?? 0)
  metrics.totalTrades = Number(summary.total_trades ?? row.total_trades ?? 0)
  metrics.winningTrades = Number(summary.winning_trades ?? 0)
  metrics.profitFactor = Number(summary.profit_factor ?? 0)
  metrics.avgWin = Number(summary.avg_win ?? 0)
  metrics.avgLoss = Number(summary.avg_loss ?? 0)

  equityCurve.value = (result?.equity_curve || result?.data?.result_data?.equity_curve || []).map((item: any) => ({
    date: String(item.date),
    equity: Number(item.equity),
    benchmark: Number(item.benchmark),
  }))

  trades.value = (result?.trades || result?.data?.result_data?.trades || []).map((trade: any) => ({
    id: Number(trade.id),
    date: String(trade.date),
    type: String(trade.type),
    price: Number(trade.price),
    quantity: Number(trade.quantity),
    profit: Number(trade.profit),
    returnPct: Number(trade.return_pct ?? trade.returnPct ?? 0),
    holdDays: Number(trade.hold_days ?? trade.holdDays ?? 0),
  }))

  hasResults.value = true
  if (result?.backtest_id) {
    currentBacktestId.value = String(result.backtest_id)
    rememberBacktestId(currentBacktestId.value)
    syncQueryFromState()
  }
}

const loadBacktestResult = async (backtestId: string) => {
  const normalizedBacktestId = String(backtestId || '').trim()
  if (!normalizedBacktestId) return
  try {
    const result = await backtestApi.getBacktest(normalizedBacktestId)
    currentBacktestId.value = normalizedBacktestId
    if (result?.status === 'completed') {
      applyBacktestResult(result)
      rememberBacktestId(normalizedBacktestId)
      showNotification?.('info', `已加载历史回测结果 #${normalizedBacktestId}`)
    }
  } catch (error) {
    showNotification?.('warning', '历史回测结果加载失败')
  }
}

const runBacktest = async () => {
  loading.value = true
  try {
    const range = resolveDateRange()
    const result = await backtestApi.runBacktest({
      strategy: config.strategyType,
      strategy_params: { ...strategyParams },
      start_date: range.start,
      end_date: range.end,
      initial_capital: config.initialCapital,
      stock_code: config.stockCode,
    } as any)

    const summary = result?.summary || {}
    metrics.initialCapital = Number(summary.initial_capital ?? config.initialCapital)
    metrics.finalCapital = Number(summary.final_capital ?? config.initialCapital)
    metrics.totalReturn = Number(summary.total_return ?? 0)
    metrics.annualizedReturn = Number(summary.annual_return ?? 0)
    metrics.maxDrawdown = Number(summary.max_drawdown ?? 0)
    metrics.sharpeRatio = Number(summary.sharpe_ratio ?? 0)
    metrics.winRate = Number(summary.win_rate ?? 0)
    metrics.totalTrades = Number(summary.total_trades ?? 0)
    metrics.winningTrades = Number(summary.winning_trades ?? 0)
    metrics.profitFactor = Number(summary.profit_factor ?? 0)
    metrics.avgWin = Number(summary.avg_win ?? 0)
    metrics.avgLoss = Number(summary.avg_loss ?? 0)

    trades.value = (result?.trades || []).map((item: any) => ({
      id: Number(item.id || 0),
      date: String(item.date || ''),
      type: String(item.type || ''),
      price: Number(item.price || 0),
      quantity: Number(item.quantity || 0),
      profit: Number(item.profit || 0),
      returnPct: Number(item.return_pct || 0),
      holdDays: Number(item.hold_days || 0),
    }))
    equityCurve.value = (result?.equity_curve || []).map((item: any) => ({
      date: String(item.date || ''),
      equity: Number(item.equity || 0),
      benchmark: Number(item.benchmark || 0),
    }))

    hasResults.value = true
    await initEquityChart()
    await loadBacktestHistory()
    showNotification?.('success', '回测完成')
  } catch (e) {
    showNotification?.('error', '回测执行失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => config.strategyType,
  () => {
    applyTemplateDefaults(selectedStrategyTemplate.value)
    syncQueryFromState()
  }
)

watch(
  () => [config.stockCode, config.period, selectedSavedStrategyId.value],
  () => {
    syncQueryFromState()
  },
  { deep: true }
)

const initEquityChart = async () => {
  if (!equityChartRef.value) return
  const points = equityCurve.value
  if (!points.length) {
    equityChartInstance.value?.clear()
    return
  }

  equityChartInstance.value = echarts.init(equityChartRef.value, 'dark', { renderer: 'canvas' })

  const dates = points.map((p) => p.date)
  const equityData = points.map((p) => p.equity)
  const benchmarkData = points.map((p) => p.benchmark)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26, 26, 26, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: 'rgba(255, 255, 255, 0.9)' },
      formatter: (params: any) => {
        let html = `<div style="font-weight: 600; margin-bottom: 8px;">${params[0].axisValue}</div>`
        params.forEach((p: any) => {
          html += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;"><span style="width:10px;height:10px;border-radius:2px;background:${p.color};"></span><span>${p.seriesName}: ${formatCurrency(p.value)}</span></div>`
        })
        return html
      },
    },
    legend: { show: false },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }, axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 }, splitLine: { show: false } },
    yAxis: {
      scale: true,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10, formatter: (value: number) => (value / 10000).toFixed(0) + '万' },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
    },
    series: [
      { name: '组合净值', type: 'line', data: equityData, smooth: true, lineStyle: { width: 2, color: '#2962FF' }, itemStyle: { color: '#2962FF' } },
      { name: '买入持有', type: 'line', data: benchmarkData, smooth: true, lineStyle: { width: 1.5, color: 'rgba(255, 255, 255, 0.4)' }, itemStyle: { color: 'rgba(255, 255, 255, 0.4)' } },
    ],
  }

  equityChartInstance.value.setOption(option)
  useResizeObserver(equityChartRef, () => equityChartInstance.value?.resize())
}

onMounted(() => {
  hydrateConfigWidth()
  configCollapsed.value = window.localStorage.getItem(PANEL_COLLAPSED_KEY) === '1'
  recentBacktests.value = JSON.parse(window.localStorage.getItem(RECENT_BACKTESTS_KEY) || '[]')
  hydrateFromQuery()
  void loadStrategyTemplates()
  void loadSavedStrategies()
  void loadBacktestHistory()
  if (currentBacktestId.value) {
    void loadBacktestResult(currentBacktestId.value)
  }
})

onBeforeUnmount(() => {
  equityChartInstance.value?.dispose()
})
</script>

<style scoped lang="scss">
.backtest-page {
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
    color: rgba(255, 255, 255, 0.9);
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }

  .backtest-id-hint {
    margin: 8px 0 0;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.45);
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .backtest-id-copy {
    border: none;
    background: transparent;
    color: rgba(255, 255, 255, 0.62);
    font-size: 12px;
    cursor: pointer;
    padding: 0;
  }
}

.header-right {
  display: flex;
  gap: 12px;
}

.btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &.btn-primary {
    background: #2962FF;
    color: white;

    &:hover:not(:disabled) {
      background: #1E53E5;
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  &.btn-secondary {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);

    &:hover {
      background: rgba(255, 255, 255, 0.12);
    }
  }
}

.spinner-small {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.backtest-layout {
  display: flex;
  gap: 12px;
}

.config-panel {
  min-width: 320px;
  max-width: 560px;
  flex-shrink: 0;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  max-height: calc(100vh - 180px);
  overflow-y: auto;
  overflow-x: hidden;
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

.config-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  &:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
  }

  h4 {
    margin: 0 0 16px;
    font-size: 14px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
  }
}

.config-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.config-item {
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }

  label {
    display: block;
    margin-bottom: 6px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.config-action {
  display: flex;
  align-items: flex-end;
}

.recent-backtests {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.history-backtests {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.history-filter-row {
  margin-bottom: 4px;
}

.history-filter,
.history-sort {
  margin-bottom: 0;
}

.recent-backtests__head {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.recent-backtests__label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.recent-backtests__clear {
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.52);
  font-size: 12px;
  cursor: pointer;
}

.recent-backtests__item {
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.78);
  padding: 6px 10px;
  cursor: pointer;
}

.history-backtests__item {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.82);
  padding: 10px 12px;
  cursor: pointer;
  text-align: left;
}

.history-backtests__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-backtests__meta {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
}

.history-backtests__stats {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.46);
}

.recent-backtests__item--history {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  border-radius: 12px;
}

.recent-backtests__item--history span {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.58);
}

.input-text,
.input-number,
.select-full {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  box-sizing: border-box;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }
}

.btn-full {
  width: 100%;
  justify-content: center;
}

.strategy-params {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
}

.strategy-description {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.55);
}

.results-panel {
  flex: 1;
  min-width: 0;
}

@media (max-width: 1200px) {
  .backtest-layout {
    flex-direction: column;
    gap: 24px;
  }

  .config-panel {
    width: 100%;
    min-width: 0;
    max-width: none;
    max-height: none;
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
  padding: 80px 40px;
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
    color: rgba(255, 255, 255, 0.9);
  }

  p {
    margin: 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.result-summary-card {
  margin-bottom: 20px;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 18px 20px;
}

.summary-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.88);
}

.summary-badge--bullish {
  background: rgba(89, 211, 140, 0.16);
}

.summary-badge--neutral {
  background: rgba(91, 163, 255, 0.16);
}

.summary-badge--flat {
  background: rgba(255, 255, 255, 0.12);
}

.summary-badge--bearish {
  background: rgba(255, 123, 123, 0.16);
}

.result-summary-text {
  margin: 0;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.7;
}

.compare-grid {
  margin-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 14px;
}

.compare-grid--metrics {
  margin-top: 12px;
}

.compare-row {
  display: grid;
  grid-template-columns: 120px 1fr 1fr;
  gap: 12px;
  padding: 6px 0;
  color: rgba(255, 255, 255, 0.72);
}

.compare-row--delta {
  grid-template-columns: 120px 1fr 1fr 100px;
}

.compare-row--head {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.48);
}

.compare-row strong {
  color: rgba(255, 255, 255, 0.9);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
}

.metric-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.metric-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.metric-badge {
  padding: 2px 8px;
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

.metric-value {
  font-size: 24px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(255, 255, 255, 0.9);
}

.metric-detail {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.charts-row {
  margin-bottom: 24px;
}

.card {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
  }
}

.chart-card {
  .chart-wrapper {
    height: 300px;
    padding: 16px;
  }
}

.chart-legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.legend-color {
  width: 12px;
  height: 3px;
  border-radius: 2px;

  &.equity {
    background: #2962FF;
  }

  &.benchmark {
    background: rgba(255, 255, 255, 0.4);
  }
}

.trades-section {
  .trades-table-wrapper {
    max-height: 400px;
    overflow-y: auto;
  }

  .trades-table {
    width: 100%;
    border-collapse: collapse;

    th,
    td {
      padding: 12px 16px;
      text-align: left;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }

    th {
      position: sticky;
      top: 0;
      background: rgba(26, 26, 26, 0.95);
      font-size: 12px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.5);
      text-transform: uppercase;
    }

    td {
      font-size: 13px;
    }
  }
}

.trade-stats {
  display: flex;
  gap: 16px;

  .stat-item {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.6);

    strong {
      font-weight: 600;
    }
  }
}

.trade-type {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;

  &.buy {
    background: rgba(0, 200, 83, 0.15);
    color: #00C853;
  }

  &.sell {
    background: rgba(255, 23, 68, 0.15);
    color: #FF1744;
  }
}

@media (max-width: 1400px) {
  .metrics-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
