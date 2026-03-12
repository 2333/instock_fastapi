<template>
  <div class="patterns-page">
    <div class="page-header">
      <div class="header-left">
        <h1>形态识别</h1>
        <p class="subtitle">使用可配置参数检测和分析图表形态</p>
      </div>
      <div class="header-right">
        <button class="btn btn-secondary" @click="showConfig = true">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          配置
        </button>
        <button class="btn btn-primary" @click="runRecognition" :disabled="loading">
          <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <span v-if="loading" class="spinner-small"></span>
          {{ loading ? '扫描中...' : '扫描形态' }}
        </button>
      </div>
    </div>

    <div class="main-content">
      <aside
        ref="filterPanelRef"
        class="filter-panel"
        :style="{ width: `${filterPanelWidth}px` }"
      >
        <div class="filter-section">
          <h4>形态类型</h4>
          <div class="filter-group">
            <label class="filter-label">反转形态</label>
            <div class="checkbox-list">
              <label v-for="pattern in reversalPatterns" :key="pattern.value" class="checkbox-item">
                <input 
                  type="checkbox" 
                  :value="pattern.value"
                  v-model="selectedPatterns"
                >
                <span class="checkbox-text">{{ pattern.label }}</span>
              </label>
            </div>
          </div>
          <div class="filter-group">
            <label class="filter-label">持续形态</label>
            <div class="checkbox-list">
              <label v-for="pattern in continuationPatterns" :key="pattern.value" class="checkbox-item">
                <input 
                  type="checkbox" 
                  :value="pattern.value"
                  v-model="selectedPatterns"
                >
                <span class="checkbox-text">{{ pattern.label }}</span>
              </label>
            </div>
          </div>
          <div class="filter-group">
            <label class="filter-label">K线形态</label>
            <div class="checkbox-list">
              <label v-for="pattern in candlestickPatterns" :key="pattern.value" class="checkbox-item">
                <input 
                  type="checkbox" 
                  :value="pattern.value"
                  v-model="selectedPatterns"
                >
                <span class="checkbox-text">{{ pattern.label }}</span>
              </label>
            </div>
          </div>
        </div>

        <div class="filter-section">
          <h4>信号筛选</h4>
          <div class="signal-filters">
            <label class="signal-option">
              <input type="checkbox" value="BULLISH" v-model="selectedSignals">
              <span class="signal-badge bullish">看涨</span>
            </label>
            <label class="signal-option">
              <input type="checkbox" value="NEUTRAL" v-model="selectedSignals">
              <span class="signal-badge neutral">中性</span>
            </label>
            <label class="signal-option">
              <input type="checkbox" value="BEARISH" v-model="selectedSignals">
              <span class="signal-badge bearish">看跌</span>
            </label>
          </div>
        </div>

        <div class="filter-section">
          <h4>日期范围</h4>
          <div class="date-inputs">
            <div class="input-group">
              <label>开始</label>
              <input type="date" v-model="dateFrom" class="input-date">
            </div>
            <div class="input-group">
              <label>结束</label>
              <input type="date" v-model="dateTo" class="input-date">
            </div>
          </div>
        </div>

        <div class="filter-section">
          <h4>技术指标筛选</h4>
          <div class="input-group">
            <label>EMA状态</label>
            <select v-model="emaSignalFilter" class="select-full">
              <option value="">全部</option>
              <option value="bullish">多头</option>
              <option value="bearish">空头</option>
              <option value="neutral">中性</option>
            </select>
          </div>
          <div class="input-group">
            <label>BOLL状态</label>
            <select v-model="bollSignalFilter" class="select-full">
              <option value="">全部</option>
              <option value="breakout">上轨突破</option>
              <option value="breakdown">下轨跌破</option>
              <option value="inside">轨道内</option>
            </select>
          </div>
          <div class="input-group">
            <label>组合逻辑</label>
            <select v-model="indicatorMode" class="select-full">
              <option value="all">AND（都满足）</option>
              <option value="any">OR（任一满足）</option>
            </select>
          </div>
        </div>

        <div class="filter-section">
          <h4>置信度</h4>
          <div class="range-slider">
            <input 
              type="range" 
              min="50" 
              max="100" 
              v-model.number="minConfidence"
              class="range-input"
            >
            <span class="range-value">{{ minConfidence }}%</span>
          </div>
        </div>

        <div class="filter-section">
          <h4>排序方式</h4>
          <select v-model="sortBy" class="select-full">
            <option value="date">日期 (最新)</option>
            <option value="confidence">置信度 (高到低)</option>
            <option value="code">股票代码</option>
          </select>
        </div>
      </aside>

      <div
        class="panel-resizer"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整形态筛选宽度"
        @mousedown="startFilterResize"
        @touchstart.prevent="startFilterResize"
      ></div>

      <main class="results-panel">
        <div class="results-header">
          <span class="results-count">共找到 {{ filteredResults.length }} 个形态</span>
          <button 
            v-if="selectedResults.length > 0" 
            class="btn btn-small"
            @click="exportResults"
          >
            导出选中 ({{ selectedResults.length }})
          </button>
        </div>

        <div class="results-table-wrapper">
          <table class="results-table">
            <thead>
              <tr>
                <th class="checkbox-col">
                  <input 
                    type="checkbox" 
                    :checked="allSelected"
                    @change="toggleSelectAll"
                  >
                </th>
                <th @click="sortBy = 'code'" class="sortable">股票</th>
                <th @click="sortBy = 'type'" class="sortable">形态类型</th>
                <th @click="sortBy = 'signal'" class="sortable">信号</th>
                <th @click="sortBy = 'confidence'" class="sortable">置信度</th>
                <th @click="sortBy = 'date'" class="sortable">日期</th>
                <th>技术信号</th>
                <th>目标/止损</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="result in paginatedResults" 
                :key="`${result.code}-${result.pattern_name}`"
              >
                <td class="checkbox-col">
                  <input
                    type="checkbox"
                    :value="`${result.code}-${result.pattern_name}-${result.trade_date}`"
                    v-model="selectedResults"
                  >
                </td>
                <td>
                  <div class="stock-cell">
                    <span class="stock-code">{{ result.code }}</span>
                    <span class="stock-name">{{ result.stock_name || '-' }}</span>
                  </div>
                </td>
                <td>
                  <span class="pattern-type">{{ getPatternLabel(result.pattern_name) }}</span>
                </td>
                <td>
                  <span class="signal-badge" :class="result.pattern_type || 'neutral'">
                    {{ getSignalText(result.pattern_type) }}
                  </span>
                </td>
                <td>
                  <div class="confidence-cell">
                    <div class="confidence-bar">
                      <div 
                        class="confidence-fill" 
                        :style="{ width: result.confidence + '%' }"
                        :class="getConfidenceClass(Number(result.confidence))"
                      ></div>
                    </div>
                    <span class="confidence-value">{{ result.confidence }}%</span>
                  </div>
                </td>
                <td>{{ result.trade_date }}</td>
                <td>
                  <div class="tech-tags">
                    <span class="tech-tag">{{ getEmaLabel(result.ema_signal) }}</span>
                    <span class="tech-tag">{{ getBollLabel(result.boll_signal) }}</span>
                  </div>
                </td>
                <td>
                  <span class="target-stop">- / -</span>
                </td>
                <td>
                  <div class="action-buttons">
                    <button class="action-btn" title="查看图表" @click="viewChart(result)">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="18" y1="20" x2="18" y2="10" />
                        <line x1="12" y1="20" x2="12" y2="4" />
                        <line x1="6" y1="20" x2="6" y2="14" />
                      </svg>
                    </button>
                    <button class="action-btn" title="加入自选" @click="addToWatchlist(result)">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <button 
            class="page-btn"
            :disabled="currentPage === 1"
            @click="currentPage--"
          >
            上一页
          </button>
          <span class="page-info">第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
          <button 
            class="page-btn"
            :disabled="currentPage === totalPages"
            @click="currentPage++"
          >
            下一页
          </button>
        </div>
      </main>
    </div>

    <Teleport to="body">
      <div v-if="showConfig" class="modal-overlay" @click.self="showConfig = false">
        <div class="modal config-modal">
          <div class="modal-header">
            <h3>形态识别配置</h3>
            <button class="close-btn" @click="showConfig = false">×</button>
          </div>
          <div class="modal-body">
            <div class="config-section">
              <h4>通用设置</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>最少K线数</label>
                  <input type="number" v-model.number="config.minBars" class="input-number">
                </div>
                <div class="config-item">
                  <label>价格容差 (%)</label>
                  <input type="number" v-model.number="config.tolerance" class="input-number">
                </div>
              </div>
            </div>

            <div class="config-section">
              <h4>头肩形态</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>肩部容差 (%)</label>
                  <input type="number" v-model.number="config.shoulderTolerance" class="input-number">
                </div>
                <div class="config-item">
                  <label>颈线容差 (%)</label>
                  <input type="number" v-model.number="config.necklineTolerance" class="input-number">
                </div>
              </div>
            </div>

            <div class="config-section">
              <h4>双顶/双底</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>价格容差 (%)</label>
                  <input type="number" v-model.number="config.doubleTopBottomTolerance" class="input-number">
                </div>
              </div>
            </div>

            <div class="config-section">
              <h4>三角形形态</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>最少点数</label>
                  <input type="number" v-model.number="config.triangleMinPoints" class="input-number">
                </div>
                <div class="config-item">
                  <label>三角形容差 (%)</label>
                  <input type="number" v-model.number="config.triangleTolerance" class="input-number">
                </div>
              </div>
            </div>

            <div class="config-section">
              <h4>突破检测</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>成交量因子</label>
                  <input type="number" v-model.number="config.breakoutVolumeFactor" class="input-number" step="0.1">
                </div>
                <div class="config-item">
                  <label>价格区间 (%)</label>
                  <input type="number" v-model.number="config.breakoutPriceRange" class="input-number">
                </div>
              </div>
            </div>

            <div class="config-section">
              <h4>技术指标参数</h4>
              <div class="config-grid">
                <div class="config-item">
                  <label>EMA 快线</label>
                  <input type="number" v-model.number="config.emaFast" class="input-number" min="2" max="120">
                </div>
                <div class="config-item">
                  <label>EMA 慢线</label>
                  <input type="number" v-model.number="config.emaSlow" class="input-number" min="3" max="250">
                </div>
                <div class="config-item">
                  <label>BOLL 周期</label>
                  <input type="number" v-model.number="config.bollPeriod" class="input-number" min="5" max="120">
                </div>
                <div class="config-item">
                  <label>BOLL 标准差</label>
                  <input type="number" v-model.number="config.bollStd" class="input-number" step="0.1" min="0.5" max="5">
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="resetConfig">重置默认</button>
            <button class="btn btn-primary" @click="applyConfig">应用更改</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { patternApi, attentionApi } from '@/api'
import { useResizablePanel } from '@/composables/useResizablePanel'

interface PatternResult {
  id?: number
  ts_code: string
  code: string
  stock_name: string
  pattern_name: string
  pattern_type: string
  confidence: number
  trade_date: string
  ema_signal?: string
  boll_signal?: string
}

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const showConfig = ref(false)
const selectedPatterns = ref<string[]>([])
const selectedSignals = ref<string[]>([])
const selectedResults = ref<string[]>([])
const currentPage = ref(1)
const pageSize = 20
const sortBy = ref<'date' | 'confidence' | 'code' | 'type' | 'signal'>('date')
const minConfidence = ref(60)
const dateFrom = ref('')
const dateTo = ref('')
const emaSignalFilter = ref('')
const bollSignalFilter = ref('')
const indicatorMode = ref<'all' | 'any'>('all')
const filterPanelRef = ref<HTMLElement | null>(null)
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')
const FILTER_PANEL_WIDTH_KEY = 'instock_patterns_panel_width'
const { panelWidth: filterPanelWidth, hydrateWidth: hydrateFilterWidth, startResize: startFilterResize } = useResizablePanel({
  panelRef: filterPanelRef,
  storageKey: FILTER_PANEL_WIDTH_KEY,
  defaultWidth: 320,
  minWidth: 280,
  maxWidth: 520,
})

const reversalPatterns = [
  { label: '晨星', value: 'MORNING_STAR' },
  { label: '夜星', value: 'EVENING_STAR' },
  { label: '看涨吞没', value: 'BULLISH_ENGULFING' },
  { label: '看跌吞没', value: 'BEARISH_ENGULFING' },
  { label: '看涨孕线', value: 'BULLISH_HARAMI' },
  { label: '看跌孕线', value: 'BEARISH_HARAMI' },
  { label: '穿刺', value: 'PIERCING' },
  { label: '乌云盖顶', value: 'DARK_CLOUD_COVER' },
]

const continuationPatterns = [
  { label: '连续上涨', value: 'CONTINUOUS_RISE' },
  { label: '连续下跌', value: 'CONTINUOUS_FALL' },
  { label: 'MA金叉', value: 'MA_GOLDEN_CROSS' },
  { label: 'MA死叉', value: 'MA_DEATH_CROSS' },
]

const candlestickPatterns = [
  { label: '突破高点', value: 'BREAKTHROUGH_HIGH' },
  { label: '跌破低点', value: 'BREAKDOWN_LOW' },
  { label: '锤子线', value: 'HAMMER' },
  { label: '倒锤子', value: 'INVERTED_HAMMER' },
  { label: '十字星', value: 'DOJI' },
  { label: '射击之星', value: 'SHOOTING_STAR' },
  { label: '吊人', value: 'HANGING_MAN' },
  { label: '光头光脚', value: 'MARUBOZU' },
  { label: '纺锤线', value: 'SPINNING_TOP' },
  { label: '龙爪', value: 'DRAGONFLY_DOJI' },
  { label: '墓碑', value: 'GRAVESTONE_DOJI' },
  { label: '红三兵', value: 'THREE_WHITE_SOLDIERS' },
  { label: '黑三鸦', value: 'THREE_BLACK_CROWS' },
  { label: '三星', value: 'TRISTAR' },
  { label: '探水杆', value: 'TAKURI' },
]

const config = reactive({
  minBars: 20,
  tolerance: 3,
  minConfidence: 60,
  shoulderTolerance: 5,
  necklineTolerance: 3,
  doubleTopBottomTolerance: 3,
  triangleMinPoints: 5,
  triangleTolerance: 2,
  breakoutVolumeFactor: 1.5,
  breakoutPriceRange: 3,
  emaFast: 12,
  emaSlow: 26,
  bollPeriod: 20,
  bollStd: 2.0,
})

const patternResults = ref<PatternResult[]>([])

const normalizeSignal = (patternType?: string | null): string => {
  const t = (patternType || '').toLowerCase()
  if (t === 'reversal' || t === 'breakout') return 'BULLISH'
  if (t === 'breakdown') return 'BEARISH'
  return 'NEUTRAL'
}

const filteredResults = computed(() => {
  const filtered = patternResults.value.filter(r => {
    if (selectedPatterns.value.length > 0 && !selectedPatterns.value.includes(r.pattern_name)) {
      return false
    }
    if (selectedSignals.value.length > 0 && !selectedSignals.value.includes(normalizeSignal(r.pattern_type))) {
      return false
    }
    if (r.confidence < minConfidence.value) {
      return false
    }
    if (dateFrom.value && r.trade_date < dateFrom.value.replaceAll('-', '')) {
      return false
    }
    if (dateTo.value && r.trade_date > dateTo.value.replaceAll('-', '')) {
      return false
    }
    if (emaSignalFilter.value && r.ema_signal !== emaSignalFilter.value) {
      return false
    }
    if (bollSignalFilter.value && r.boll_signal !== bollSignalFilter.value) {
      return false
    }
    return true
  })

  filtered.sort((a, b) => {
    if (sortBy.value === 'confidence') return b.confidence - a.confidence
    if (sortBy.value === 'code') return (a.code || '').localeCompare(b.code || '')
    if (sortBy.value === 'type') return (a.pattern_name || '').localeCompare(b.pattern_name || '')
    if (sortBy.value === 'signal') return normalizeSignal(a.pattern_type).localeCompare(normalizeSignal(b.pattern_type))
    return (b.trade_date || '').localeCompare(a.trade_date || '')
  })

  return filtered
})

const totalPages = computed(() => Math.ceil(filteredResults.value.length / pageSize))
const allSelected = computed(() => {
  const current = paginatedResults.value
  return current.length > 0 && current.every(item => selectedResults.value.includes(`${item.code}-${item.pattern_name}-${item.trade_date}`))
})

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredResults.value.slice(start, start + pageSize)
})

const getConfidenceClass = (confidence: number) => {
  if (confidence >= 80) return 'high'
  if (confidence >= 60) return 'medium'
  return 'low'
}

const getSignalText = (type: string | null) => {
  const normalized = normalizeSignal(type)
  if (normalized === 'BULLISH') return '看涨'
  if (normalized === 'BEARISH') return '看跌'
  return '中性'
}

const getPatternLabel = (name: string) => {
  const labels: Record<string, string> = {
    'MORNING_STAR': '晨星',
    'EVENING_STAR': '夜星',
    'BREAKTHROUGH_HIGH': '突破高点',
    'BREAKDOWN_LOW': '跌破低点',
    'CONTINUOUS_RISE': '连续上涨',
    'CONTINUOUS_FALL': '连续下跌',
    'BULLISH_ENGULFING': '看涨吞没',
    'BEARISH_ENGULFING': '看跌吞没',
    'BULLISH_HARAMI': '看涨孕线',
    'BEARISH_HARAMI': '看跌孕线',
    'HAMMER': '锤子线',
    'INVERTED_HAMMER': '倒锤子',
    'DOJI': '十字星',
    'SPINNING_TOP': '纺锤线',
    'MARUBOZU': '光头光脚',
    'SHOOTING_STAR': '射击之星',
    'PIERCING': '穿刺',
    'DARK_CLOUD_COVER': '乌云盖顶',
    'HANGING_MAN': '吊人',
    'DRAGONFLY_DOJI': '龙爪',
    'GRAVESTONE_DOJI': '墓碑',
    'TRISTAR': '三星',
    'TAKURI': '探水杆',
    'THREE_WHITE_SOLDIERS': '红三兵',
    'THREE_BLACK_CROWS': '黑三鸦',
    'MA_GOLDEN_CROSS': 'MA金叉',
    'MA_DEATH_CROSS': 'MA死叉',
  }
  return labels[name] || name
}

const getEmaLabel = (signal?: string) => {
  if (signal === 'bullish') return 'EMA: 多头'
  if (signal === 'bearish') return 'EMA: 空头'
  if (signal === 'neutral') return 'EMA: 中性'
  return 'EMA: NoData'
}

const getBollLabel = (signal?: string) => {
  if (signal === 'breakout') return 'BOLL: 上破'
  if (signal === 'breakdown') return 'BOLL: 下破'
  if (signal === 'inside') return 'BOLL: 轨内'
  return 'BOLL: NoData'
}

const fetchPatterns = async () => {
  loading.value = true
  try {
    const data = await patternApi.getTodayPatterns({
      limit: 300,
      min_confidence: minConfidence.value,
      start_date: dateFrom.value ? dateFrom.value.replaceAll('-', '') : undefined,
      end_date: dateTo.value ? dateTo.value.replaceAll('-', '') : undefined,
      pattern_names: selectedPatterns.value.length > 0 ? selectedPatterns.value.join(',') : undefined,
      ema_fast: config.emaFast,
      ema_slow: config.emaSlow,
      boll_period: config.bollPeriod,
      boll_std: config.bollStd,
      ema_signal: emaSignalFilter.value || undefined,
      boll_signal: bollSignalFilter.value || undefined,
      indicator_mode: indicatorMode.value,
    })
    patternResults.value = (data || []).map((p: any) => ({
      ...p,
      code: p.code || p.symbol || p.ts_code?.split('.')[0],
    }))
    selectedResults.value = []
    currentPage.value = 1
  } catch (e) {
    console.error('Failed to fetch patterns:', e)
    patternResults.value = []
  } finally {
    loading.value = false
  }
}

const runRecognition = async () => {
  await fetchPatterns()
}

const toggleSelectAll = () => {
  const currentIds = paginatedResults.value.map((item) => `${item.code}-${item.pattern_name}-${item.trade_date}`)
  if (allSelected.value) {
    selectedResults.value = selectedResults.value.filter((id) => !currentIds.includes(id))
  } else {
    selectedResults.value = Array.from(new Set([...selectedResults.value, ...currentIds]))
  }
}

const exportResults = () => {
  const selected = filteredResults.value.filter((item) =>
    selectedResults.value.includes(`${item.code}-${item.pattern_name}-${item.trade_date}`)
  )
  if (selected.length === 0) return
  const blob = new Blob([JSON.stringify(selected, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `patterns_${new Date().toISOString().slice(0, 10)}.json`
  link.click()
  URL.revokeObjectURL(url)
}

const resetConfig = () => {
  config.minBars = 20
  config.tolerance = 3
  config.minConfidence = 60
  config.shoulderTolerance = 5
  config.necklineTolerance = 3
  config.doubleTopBottomTolerance = 3
  config.triangleMinPoints = 5
  config.triangleTolerance = 2
  config.breakoutVolumeFactor = 1.5
  config.breakoutPriceRange = 3
  config.emaFast = 12
  config.emaSlow = 26
  config.bollPeriod = 20
  config.bollStd = 2
  minConfidence.value = 60
  emaSignalFilter.value = ''
  bollSignalFilter.value = ''
  indicatorMode.value = 'all'
}

const applyConfig = () => {
  showConfig.value = false
  fetchPatterns()
}

const viewChart = (result: PatternResult) => {
  router.push(`/stock/${result.code}`)
}

const addToWatchlist = async (result: PatternResult) => {
  try {
    await attentionApi.add(result.code)
    showNotification?.('success', `已添加 ${result.stock_name || result.code} 到关注列表`)
  } catch (e) {
    console.error('Failed to add to watchlist:', e)
    showNotification?.('error', '添加关注失败')
  }
}

onMounted(() => {
  hydrateFilterWidth()
  const queryCode = String(route.query.code || '').trim()
  if (queryCode) {
    selectedPatterns.value = []
  }
  fetchPatterns()
})
</script>

<style scoped lang="scss">
.patterns-page {
  padding: 24px;
  height: 100%;
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

  &.btn-small {
    padding: 6px 12px;
    font-size: 12px;
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

.main-content {
  display: flex;
  gap: 12px;
  height: calc(100% - 100px);
}

.filter-panel {
  flex-shrink: 0;
  min-width: 280px;
  max-width: 520px;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
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

.filter-section {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }

  h4 {
    margin: 0 0 12px;
    font-size: 13px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.6);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.filter-group {
  margin-bottom: 16px;
}

.filter-label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.checkbox-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;

  input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: #2962FF;
  }

  .checkbox-text {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
  }
}

.signal-filters {
  display: flex;
  gap: 8px;
}

.signal-option {
  cursor: pointer;

  input {
    display: none;
  }
}

.signal-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  transition: all 0.2s;

  &.bullish {
    background: rgba(0, 200, 83, 0.15);
    color: #00C853;
  }

  &.bearish {
    background: rgba(255, 23, 68, 0.15);
    color: #FF1744;
  }

  &.neutral {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.6);
  }
}

.signal-option input:checked + .signal-badge {
  box-shadow: 0 0 0 2px rgba(41, 98, 255, 0.5);
}

.date-inputs {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group {
  label {
    display: block;
    margin-bottom: 4px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.4);
  }
}

.input-date,
.select-full {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  box-sizing: border-box;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }
}

.range-slider {
  display: flex;
  align-items: center;
  gap: 12px;
}

.range-input {
  flex: 1;
  height: 4px;
  -webkit-appearance: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;

  &::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #2962FF;
    cursor: pointer;
  }
}

.range-value {
  font-size: 14px;
  font-weight: 600;
  color: #2962FF;
  min-width: 40px;
}

.results-panel {
  flex: 1;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.results-count {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.results-table-wrapper {
  flex: 1;
  overflow: auto;
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
    position: sticky;
    top: 0;
    background: rgba(26, 26, 26, 0.95);
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    z-index: 1;

    &.sortable {
      cursor: pointer;

      &:hover {
        color: rgba(255, 255, 255, 0.8);
      }
    }
  }

  td {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.8);
  }

  tr {
    transition: background 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.02);
    }

    &.selected {
      background: rgba(41, 98, 255, 0.05);
    }
  }
}

.checkbox-col {
  width: 40px;
}

.stock-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .stock-code {
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }

.stock-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.tech-tags {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tech-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.75);
  background: rgba(255, 255, 255, 0.08);
}
}

.pattern-type {
  font-size: 12px;
}

.confidence-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-bar {
  width: 60px;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s;

  &.high {
    background: #00C853;
  }

  &.medium {
    background: #FF9800;
  }

  &.low {
    background: #FF1744;
  }
}

.confidence-value {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.price-targets {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;

  .target {
    color: #00C853;
  }

  .stop {
    color: #FF1744;
  }
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.page-btn {
  padding: 8px 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.2);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.page-info {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

@media (max-width: 1200px) {
  .main-content {
    flex-direction: column;
    gap: 24px;
    height: auto;
  }

  .filter-panel {
    width: 100%;
    min-width: 0;
    max-width: none;
    max-height: 50vh;
  }

  .panel-resizer {
    display: none;
  }
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.config-modal {
  width: 600px;
  max-height: 80vh;
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}

.modal-header {
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

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 20px;
  cursor: pointer;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.config-section {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }

  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
  }
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.config-item {
  label {
    display: block;
    margin-bottom: 6px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.input-number {
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

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
