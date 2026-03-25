<template>
  <div class="patterns-page">
    <div class="page-header">
      <div class="header-left">
        <h1>形态识别</h1>
        <p class="subtitle">按股票聚合结果，在同一只股票下展开多个形态子行。</p>
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
          <h4>股票筛选</h4>
          <div class="input-group">
            <label>代码 / 名称</label>
            <input
              v-model.trim="stockKeyword"
              type="text"
              class="input-text"
              placeholder="仅过滤当前扫描结果"
            >
            <p class="filter-hint">当前仅在已加载的结果中按代码或名称过滤。</p>
          </div>
        </div>

        <div class="filter-section">
          <h4>评估时间范围</h4>
          <div class="range-presets">
            <button
              v-for="preset in rangePresetOptions"
              :key="preset.value"
              class="preset-btn"
              :class="{ active: rangePreset === preset.value }"
              @click="selectRangePreset(preset.value)"
            >
              {{ preset.label }}
            </button>
          </div>
          <div class="date-inputs">
            <div class="input-group">
              <label>开始</label>
              <input type="date" v-model="dateFrom" class="input-date" @input="rangePreset = 'custom'">
            </div>
            <div class="input-group">
              <label>结束</label>
              <input type="date" v-model="dateTo" class="input-date" @input="rangePreset = 'custom'">
            </div>
          </div>
          <p class="filter-hint">{{ currentEvaluationRangeLabel }}</p>
        </div>
        <div class="filter-section">
          <h4>形态类型</h4>
          <div class="filter-group">
            <label class="filter-label">反转形态</label>
            <div class="checkbox-list">
              <label v-for="pattern in reversalPatterns" :key="pattern.value" class="checkbox-item">
                <input
                  v-model="selectedPatterns"
                  type="checkbox"
                  :value="pattern.value"
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
                  v-model="selectedPatterns"
                  type="checkbox"
                  :value="pattern.value"
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
                  v-model="selectedPatterns"
                  type="checkbox"
                  :value="pattern.value"
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
              <input v-model="selectedSignals" type="checkbox" value="BULLISH">
              <span class="signal-badge bullish">看涨</span>
            </label>
            <label class="signal-option">
              <input v-model="selectedSignals" type="checkbox" value="NEUTRAL">
              <span class="signal-badge neutral">中性</span>
            </label>
            <label class="signal-option">
              <input v-model="selectedSignals" type="checkbox" value="BEARISH">
              <span class="signal-badge bearish">看跌</span>
            </label>
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
              v-model.number="minConfidence"
              type="range"
              min="50"
              max="100"
              class="range-input"
            >
            <span class="range-value">{{ minConfidence }}%</span>
          </div>
        </div>

        <div class="filter-section">
          <h4>排序方式</h4>
          <select v-model="sortBy" class="select-full">
            <option value="confidence">最高置信度</option>
            <option value="date">最新形态日期</option>
            <option value="pattern_count">命中形态数</option>
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
          <div class="results-summary">
            <span class="results-count">共找到 {{ groupedResults.length }} 只股票</span>
            <span class="summary-chip">形态子行 {{ totalPatternRows }}</span>
            <span class="summary-chip">区间内出现 {{ totalOccurrences }} 次</span>
            <span class="summary-chip accent">{{ currentEvaluationRangeLabel }}</span>
          </div>
          <button
            v-if="selectedStocks.length > 0"
            class="btn btn-small"
            @click="exportResults"
          >
            导出选中 ({{ selectedStocks.length }})
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
                <th>形态</th>
                <th>信号</th>
                <th @click="sortBy = 'confidence'" class="sortable">置信度</th>
                <th @click="sortBy = 'date'" class="sortable">最新出现</th>
                <th>技术信号</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <template v-if="paginatedGroups.length > 0">
                <template v-for="stock in paginatedGroups" :key="stock.groupKey">
                  <tr
                    v-for="(pattern, index) in getVisiblePatternRows(stock)"
                    :key="pattern.rowKey"
                    class="result-row"
                    :class="{ 'group-start': index === 0 }"
                  >
                    <td
                      v-if="index === 0"
                      class="checkbox-col merged-cell"
                      :rowspan="getVisiblePatternCount(stock)"
                    >
                      <input
                        v-model="selectedStocks"
                        type="checkbox"
                        :value="stock.groupKey"
                      >
                    </td>
                    <td
                      v-if="index === 0"
                      class="merged-cell stock-merged"
                      :rowspan="getVisiblePatternCount(stock)"
                    >
                      <div class="stock-cell">
                        <span class="stock-code">{{ stock.code }}</span>
                        <span class="stock-name">{{ stock.stock_name || '-' }}</span>
                      </div>
                      <div class="stock-summary">
                        <span>最高 {{ formatConfidence(stock.maxConfidence) }}</span>
                        <span>{{ stock.patternRows.length }} 个形态</span>
                        <button
                          v-if="stock.patternRows.length > collapsedPatternLimit"
                          class="collapse-toggle"
                          @click="togglePatternRows(stock.groupKey)"
                        >
                          {{ isPatternGroupExpanded(stock.groupKey) ? '收起' : `展开剩余 ${stock.patternRows.length - collapsedPatternLimit} 个` }}
                        </button>
                      </div>
                    </td>

                    <td>
                      <div class="pattern-name-row">
                        <span class="pattern-type">{{ getPatternLabel(pattern.pattern_name) }}</span>
                        <span
                          v-if="pattern.occurrenceCount > 1"
                          class="pattern-count-badge"
                          :title="getPatternOccurrenceHint(pattern)"
                        >
                          {{ pattern.occurrenceCount }}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span class="signal-badge" :class="normalizeSignalClass(pattern.latest.pattern_type)">
                        {{ getSignalText(pattern.latest.pattern_type) }}
                      </span>
                    </td>
                    <td>
                      <div class="confidence-cell">
                        <div class="confidence-bar">
                          <div
                            class="confidence-fill"
                            :style="{ width: `${pattern.latest.confidence}%` }"
                            :class="getConfidenceClass(pattern.latest.confidence)"
                          ></div>
                        </div>
                        <span class="confidence-value">{{ formatConfidence(pattern.latest.confidence) }}</span>
                      </div>
                    </td>
                    <td>
                      <div class="date-cell">
                        <span>{{ formatDisplayDate(pattern.latest.trade_date) }}</span>
                        <span class="date-caption">区间内最新一次</span>
                      </div>
                    </td>
                    <td>
                      <div class="tech-tags">
                        <span class="tech-tag">{{ getEmaLabel(pattern.latest.ema_signal) }}</span>
                        <span class="tech-tag">{{ getBollLabel(pattern.latest.boll_signal) }}</span>
                      </div>
                    </td>

                    <td
                      v-if="index === 0"
                      class="merged-cell action-merged"
                      :rowspan="getVisiblePatternCount(stock)"
                    >
                      <div class="action-stack">
                        <button class="action-btn" title="查看图表" @click="viewChart(stock)">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="18" y1="20" x2="18" y2="10" />
                            <line x1="12" y1="20" x2="12" y2="4" />
                            <line x1="6" y1="20" x2="6" y2="14" />
                          </svg>
                        </button>
                        <button class="action-btn" title="加入自选" @click="addToWatchlist(stock)">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                </template>
              </template>
              <tr v-else>
                <td colspan="8" class="empty-row">
                  当前条件下没有匹配的股票。
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
import { computed, inject, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { attentionApi, patternApi } from '@/api'
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

interface PatternRowGroup {
  rowKey: string
  pattern_name: string
  latest: PatternResult
  occurrences: PatternResult[]
  occurrenceCount: number
}

interface PatternStockGroup {
  groupKey: string
  ts_code: string
  code: string
  stock_name: string
  patternRows: PatternRowGroup[]
  maxConfidence: number
  latestTradeDate: string
  totalOccurrences: number
}

const collapsedPatternLimit = 3

type RangePreset = 'latest' | '5d' | '20d' | '60d' | 'custom'
type SortOption = 'confidence' | 'date' | 'code' | 'pattern_count'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const showConfig = ref(false)
const selectedPatterns = ref<string[]>([])
const selectedSignals = ref<string[]>([])
const selectedStocks = ref<string[]>([])
const expandedPatternGroups = ref<string[]>([])
const stockKeyword = ref('')
const currentPage = ref(1)
const pageSize = 20
const sortBy = ref<SortOption>('confidence')
const minConfidence = ref(60)
const dateFrom = ref('')
const dateTo = ref('')
const rangePreset = ref<RangePreset>('latest')
const latestEvaluatedDate = ref('')
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

const rangePresetOptions = [
  { label: '最新评估日', value: 'latest' as const },
  { label: '近5日', value: '5d' as const },
  { label: '近20日', value: '20d' as const },
  { label: '近60日', value: '60d' as const },
  { label: '自定义', value: 'custom' as const },
]

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

const parseDateValue = (value?: string | null): Date => {
  if (!value) return new Date(NaN)
  if (value.includes('-')) return new Date(`${value}T00:00:00`)
  const year = Number(value.slice(0, 4))
  const month = Number(value.slice(4, 6)) - 1
  const day = Number(value.slice(6, 8))
  return new Date(year, month, day)
}

const formatCompactDate = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

const formatInputDate = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const todayCompactDate = () => formatCompactDate(new Date())

const shiftCompactDate = (value: string, days: number) => {
  const base = parseDateValue(value)
  if (Number.isNaN(base.getTime())) return todayCompactDate()
  base.setDate(base.getDate() + days)
  return formatCompactDate(base)
}

const toCompactRangeValue = (value: string) => value ? value.split('-').join('') : ''

const formatDisplayDate = (value?: string | null) => {
  if (!value) return '-'
  if (value.includes('-')) return value
  if (value.length !== 8) return value
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
}

const normalizeSignal = (patternType?: string | null): 'BULLISH' | 'BEARISH' | 'NEUTRAL' => {
  const t = (patternType || '').toLowerCase()
  if (t === 'reversal' || t === 'breakout') return 'BULLISH'
  if (t === 'breakdown') return 'BEARISH'
  return 'NEUTRAL'
}

const normalizeSignalClass = (patternType?: string | null) => normalizeSignal(patternType).toLowerCase()

const getSignalText = (type: string | null) => {
  const normalized = normalizeSignal(type)
  if (normalized === 'BULLISH') return '看涨'
  if (normalized === 'BEARISH') return '看跌'
  return '中性'
}

const getPatternLabel = (name: string) => {
  const labels: Record<string, string> = {
    MORNING_STAR: '晨星',
    EVENING_STAR: '夜星',
    BREAKTHROUGH_HIGH: '突破高点',
    BREAKDOWN_LOW: '跌破低点',
    CONTINUOUS_RISE: '连续上涨',
    CONTINUOUS_FALL: '连续下跌',
    BULLISH_ENGULFING: '看涨吞没',
    BEARISH_ENGULFING: '看跌吞没',
    BULLISH_HARAMI: '看涨孕线',
    BEARISH_HARAMI: '看跌孕线',
    HAMMER: '锤子线',
    INVERTED_HAMMER: '倒锤子',
    DOJI: '十字星',
    SPINNING_TOP: '纺锤线',
    MARUBOZU: '光头光脚',
    SHOOTING_STAR: '射击之星',
    PIERCING: '穿刺',
    DARK_CLOUD_COVER: '乌云盖顶',
    HANGING_MAN: '吊人',
    DRAGONFLY_DOJI: '龙爪',
    GRAVESTONE_DOJI: '墓碑',
    TRISTAR: '三星',
    TAKURI: '探水杆',
    THREE_WHITE_SOLDIERS: '红三兵',
    THREE_BLACK_CROWS: '黑三鸦',
    MA_GOLDEN_CROSS: 'MA金叉',
    MA_DEATH_CROSS: 'MA死叉',
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

const getConfidenceClass = (confidence: number) => {
  if (confidence >= 80) return 'high'
  if (confidence >= 60) return 'medium'
  return 'low'
}

const formatConfidence = (confidence?: number | null) => `${Math.round(Number(confidence || 0))}%`

const currentEvaluationRange = computed(() => {
  if (rangePreset.value === 'latest') {
    if (latestEvaluatedDate.value) {
      return {
        start: latestEvaluatedDate.value,
        end: latestEvaluatedDate.value,
        label: `评估区间：最新评估日 ${formatDisplayDate(latestEvaluatedDate.value)}`,
      }
    }
    return {
      start: '',
      end: '',
      label: '评估区间：最新评估日',
    }
  }

  const start = toCompactRangeValue(dateFrom.value)
  const end = toCompactRangeValue(dateTo.value)

  if (start && end) {
    return {
      start,
      end,
      label: `评估区间：${formatDisplayDate(start)} 至 ${formatDisplayDate(end)}`,
    }
  }
  if (start) {
    return {
      start,
      end: '',
      label: `评估区间：自 ${formatDisplayDate(start)} 起`,
    }
  }
  if (end) {
    return {
      start: '',
      end,
      label: `评估区间：截至 ${formatDisplayDate(end)}`,
    }
  }

  return {
    start: '',
    end: '',
    label: '评估区间：自定义',
  }
})

const currentEvaluationRangeLabel = computed(() => currentEvaluationRange.value.label)

const filteredOccurrences = computed(() =>
  patternResults.value.filter((result) => {
    if (rangePreset.value === 'latest' && latestEvaluatedDate.value && result.trade_date !== latestEvaluatedDate.value) {
      return false
    }
    if (selectedPatterns.value.length > 0 && !selectedPatterns.value.includes(result.pattern_name)) {
      return false
    }
    if (selectedSignals.value.length > 0 && !selectedSignals.value.includes(normalizeSignal(result.pattern_type))) {
      return false
    }
    if (result.confidence < minConfidence.value) {
      return false
    }
    const rangeStart = toCompactRangeValue(dateFrom.value)
    const rangeEnd = toCompactRangeValue(dateTo.value)
    if (rangeStart && result.trade_date < rangeStart) {
      return false
    }
    if (rangeEnd && result.trade_date > rangeEnd) {
      return false
    }
    if (emaSignalFilter.value && result.ema_signal !== emaSignalFilter.value) {
      return false
    }
    if (bollSignalFilter.value && result.boll_signal !== bollSignalFilter.value) {
      return false
    }
    return true
  })
)

const groupedResults = computed<PatternStockGroup[]>(() => {
  const byStock = new Map<string, PatternResult[]>()

  for (const result of filteredOccurrences.value) {
    const key = result.code || result.ts_code
    if (!key) continue
    if (!byStock.has(key)) byStock.set(key, [])
    byStock.get(key)!.push(result)
  }

  let groups = Array.from(byStock.entries()).map(([stockKey, rows]) => {
    const byPattern = new Map<string, PatternResult[]>()

    for (const row of rows) {
      if (!byPattern.has(row.pattern_name)) byPattern.set(row.pattern_name, [])
      byPattern.get(row.pattern_name)!.push(row)
    }

    const patternRows = Array.from(byPattern.entries()).map(([patternName, occurrences]) => {
      const sortedOccurrences = [...occurrences].sort((a, b) => {
        const dateDiff = (b.trade_date || '').localeCompare(a.trade_date || '')
        if (dateDiff !== 0) return dateDiff
        return (b.confidence || 0) - (a.confidence || 0)
      })
      return {
        rowKey: `${stockKey}-${patternName}`,
        pattern_name: patternName,
        latest: sortedOccurrences[0],
        occurrences: sortedOccurrences,
        occurrenceCount: sortedOccurrences.length,
      }
    })

    patternRows.sort((a, b) => {
      const confidenceDiff = (b.latest.confidence || 0) - (a.latest.confidence || 0)
      if (confidenceDiff !== 0) return confidenceDiff
      return (b.latest.trade_date || '').localeCompare(a.latest.trade_date || '')
    })

    const first = rows[0]
    return {
      groupKey: stockKey,
      ts_code: first.ts_code,
      code: first.code,
      stock_name: first.stock_name,
      patternRows,
      maxConfidence: Math.max(...patternRows.map((row) => Number(row.latest.confidence || 0))),
      latestTradeDate: patternRows.reduce((latest, row) => row.latest.trade_date > latest ? row.latest.trade_date : latest, ''),
      totalOccurrences: patternRows.reduce((sum, row) => sum + row.occurrenceCount, 0),
    }
  })

  const keyword = stockKeyword.value.trim().toLowerCase()
  if (keyword) {
    groups = groups.filter((group) => {
      const code = (group.code || '').toLowerCase()
      const name = (group.stock_name || '').toLowerCase()
      return code.includes(keyword) || name.includes(keyword)
    })
  }

  groups.sort((a, b) => {
    if (sortBy.value === 'code') {
      return (a.code || '').localeCompare(b.code || '')
    }
    if (sortBy.value === 'pattern_count') {
      const countDiff = b.patternRows.length - a.patternRows.length
      if (countDiff !== 0) return countDiff
      return b.maxConfidence - a.maxConfidence
    }
    if (sortBy.value === 'date') {
      const dateDiff = (b.latestTradeDate || '').localeCompare(a.latestTradeDate || '')
      if (dateDiff !== 0) return dateDiff
      return b.maxConfidence - a.maxConfidence
    }
    const confidenceDiff = b.maxConfidence - a.maxConfidence
    if (confidenceDiff !== 0) return confidenceDiff
    return (b.latestTradeDate || '').localeCompare(a.latestTradeDate || '')
  })

  return groups
})

const isPatternGroupExpanded = (groupKey: string) => expandedPatternGroups.value.includes(groupKey)

const getVisiblePatternRows = (group: PatternStockGroup) => (
  isPatternGroupExpanded(group.groupKey) ? group.patternRows : group.patternRows.slice(0, collapsedPatternLimit)
)

const getVisiblePatternCount = (group: PatternStockGroup) => getVisiblePatternRows(group).length

const togglePatternRows = (groupKey: string) => {
  if (expandedPatternGroups.value.includes(groupKey)) {
    expandedPatternGroups.value = expandedPatternGroups.value.filter((item) => item !== groupKey)
    return
  }
  expandedPatternGroups.value = [...expandedPatternGroups.value, groupKey]
}

const totalPatternRows = computed(() =>
  groupedResults.value.reduce((sum, group) => sum + group.patternRows.length, 0)
)

const totalOccurrences = computed(() =>
  groupedResults.value.reduce((sum, group) => sum + group.totalOccurrences, 0)
)

const totalPages = computed(() => Math.max(1, Math.ceil(groupedResults.value.length / pageSize)))

const paginatedGroups = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return groupedResults.value.slice(start, start + pageSize)
})

const allSelected = computed(() => {
  const current = paginatedGroups.value
  return current.length > 0 && current.every((item) => selectedStocks.value.includes(item.groupKey))
})

const getPatternOccurrenceHint = (pattern: PatternRowGroup) =>
  `${getPatternLabel(pattern.pattern_name)} 在当前评估区间共出现 ${pattern.occurrenceCount} 次，更多标记请到股票详情查看。`

const selectRangePreset = (preset: RangePreset) => {
  rangePreset.value = preset
  if (preset === 'latest') {
    dateFrom.value = ''
    dateTo.value = ''
    return
  }
  if (preset === 'custom') {
    return
  }

  const span = preset === '5d' ? 5 : preset === '20d' ? 20 : 60
  const anchor = latestEvaluatedDate.value || toCompactRangeValue(dateTo.value) || todayCompactDate()
  const end = anchor
  const start = shiftCompactDate(anchor, -(span - 1))
  dateFrom.value = formatInputDate(parseDateValue(start))
  dateTo.value = formatInputDate(parseDateValue(end))
}

const fetchPatterns = async () => {
  loading.value = true
  try {
    const useExplicitRange = rangePreset.value !== 'latest'
    const data = await patternApi.getTodayPatterns({
      limit: 300,
      min_confidence: minConfidence.value,
      start_date: useExplicitRange ? toCompactRangeValue(dateFrom.value) || undefined : undefined,
      end_date: useExplicitRange ? toCompactRangeValue(dateTo.value) || undefined : undefined,
      pattern_names: selectedPatterns.value.length > 0 ? selectedPatterns.value.join(',') : undefined,
      ema_fast: config.emaFast,
      ema_slow: config.emaSlow,
      boll_period: config.bollPeriod,
      boll_std: config.bollStd,
      ema_signal: emaSignalFilter.value || undefined,
      boll_signal: bollSignalFilter.value || undefined,
      indicator_mode: indicatorMode.value,
    })

    patternResults.value = (data || []).map((pattern: any) => ({
      ...pattern,
      code: pattern.code || pattern.symbol || pattern.ts_code?.split('.')[0],
      confidence: Number(pattern.confidence || 0),
      trade_date: pattern.trade_date || '',
    }))

    latestEvaluatedDate.value = patternResults.value.reduce((latest, row) => row.trade_date > latest ? row.trade_date : latest, '')
    selectedStocks.value = []
    expandedPatternGroups.value = []
    currentPage.value = 1
  } catch (error) {
    console.error('Failed to fetch patterns:', error)
    patternResults.value = []
    latestEvaluatedDate.value = ''
  } finally {
    loading.value = false
  }
}

const runRecognition = async () => {
  await fetchPatterns()
}

const toggleSelectAll = () => {
  const currentIds = paginatedGroups.value.map((item) => item.groupKey)
  if (allSelected.value) {
    selectedStocks.value = selectedStocks.value.filter((id) => !currentIds.includes(id))
  } else {
    selectedStocks.value = Array.from(new Set([...selectedStocks.value, ...currentIds]))
  }
}

const exportResults = () => {
  const selected = groupedResults.value.filter((item) => selectedStocks.value.includes(item.groupKey))
  if (selected.length === 0) return
  const payload = {
    exported_at: new Date().toISOString(),
    evaluation_range: currentEvaluationRange.value,
    items: selected,
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' })
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

const viewChart = (group: PatternStockGroup) => {
  const query: Record<string, string> = {}
  if (currentEvaluationRange.value.start) query.pattern_start = currentEvaluationRange.value.start
  if (currentEvaluationRange.value.end) query.pattern_end = currentEvaluationRange.value.end

  router.push({
    path: `/stock/${group.code}`,
    query,
  })
}

const addToWatchlist = async (group: PatternStockGroup) => {
  try {
    await attentionApi.add(group.code)
    showNotification?.('success', `已添加 ${group.stock_name || group.code} 到关注列表`)
  } catch (error) {
    console.error('Failed to add to watchlist:', error)
    showNotification?.('error', '添加关注失败')
  }
}

watch(groupedResults, (groups) => {
  const availableKeys = new Set(groups.map((group) => group.groupKey))
  expandedPatternGroups.value = expandedPatternGroups.value.filter((key) => availableKeys.has(key))
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value
  }
}, { deep: false })

onMounted(() => {
  hydrateFilterWidth()
  const queryCode = String(route.query.code || '').trim()
  if (queryCode) {
    stockKeyword.value = queryCode
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
    color: rgba(255, 255, 255, 0.92);
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.52);
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
    color: #fff;

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
    color: rgba(255, 255, 255, 0.82);

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
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
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
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
  background:
    radial-gradient(circle at top left, rgba(41, 98, 255, 0.12), transparent 38%),
    rgba(26, 26, 26, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
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
    color: rgba(255, 255, 255, 0.62);
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

.filter-hint {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.44);
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

  input[type='checkbox'] {
    width: 16px;
    height: 16px;
    accent-color: #2962FF;
  }

  .checkbox-text {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.76);
  }
}

.signal-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.signal-option {
  cursor: pointer;

  input {
    display: none;
  }
}

.signal-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  padding: 4px 10px;
  border-radius: 999px;
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
    color: rgba(255, 255, 255, 0.68);
  }
}

.signal-option input:checked + .signal-badge {
  box-shadow: 0 0 0 2px rgba(41, 98, 255, 0.45);
}

.range-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.preset-btn {
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.74);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(41, 98, 255, 0.45);
    color: rgba(255, 255, 255, 0.9);
  }

  &.active {
    background: rgba(41, 98, 255, 0.14);
    border-color: rgba(41, 98, 255, 0.72);
    color: #8fb0ff;
  }
}

.date-inputs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.input-group {
  label {
    display: block;
    margin-bottom: 4px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.42);
  }
}

.input-text,
.input-date,
.select-full,
.input-number {
  width: 100%;
  box-sizing: border-box;
  padding: 9px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(7, 13, 24, 0.74);
  color: rgba(255, 255, 255, 0.92);
  font-size: 13px;
  color-scheme: dark;

  &:focus {
    outline: none;
    border-color: rgba(41, 98, 255, 0.88);
    box-shadow: 0 0 0 3px rgba(41, 98, 255, 0.16);
  }
}

.select-full {
  appearance: none;
  padding-right: 36px;
  background-image:
    linear-gradient(45deg, transparent 50%, rgba(255, 255, 255, 0.7) 50%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.7) 50%, transparent 50%);
  background-position:
    calc(100% - 18px) calc(50% - 2px),
    calc(100% - 12px) calc(50% - 2px);
  background-size: 6px 6px, 6px 6px;
  background-repeat: no-repeat;

  option {
    background: #0e1524;
    color: rgba(255, 255, 255, 0.92);
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
  min-width: 42px;
  font-size: 14px;
  font-weight: 600;
  color: #8fb0ff;
}

.results-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(41, 98, 255, 0.08), transparent 120px),
    rgba(26, 26, 26, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.results-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.results-count {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.72);
}

.summary-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;

  &.accent {
    background: rgba(41, 98, 255, 0.14);
    color: #a2bcff;
  }
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
    z-index: 1;
    background: rgba(11, 16, 25, 0.94);
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.52);
    text-transform: uppercase;
    letter-spacing: 0.5px;

    &.sortable {
      cursor: pointer;

      &:hover {
        color: rgba(255, 255, 255, 0.82);
      }
    }
  }

  td {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.84);
    vertical-align: middle;
  }
}

.result-row:hover {
  background: rgba(255, 255, 255, 0.025);
}

.group-start td {
  border-top: 1px solid rgba(41, 98, 255, 0.12);
}

.merged-cell {
  vertical-align: top;
}

.checkbox-col {
  width: 48px;
}

.stock-merged {
  min-width: 180px;
}

.stock-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stock-code {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.94);
}

.stock-name {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.52);
}

.stock-summary {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  margin-top: 10px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.48);
}

.collapse-toggle {
  padding: 0;
  border: none;
  background: transparent;
  color: #8fb7ff;
  font-size: 12px;
  cursor: pointer;
}

.collapse-toggle:hover {
  color: #c4d8ff;
}

.pattern-name-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.pattern-type {
  font-weight: 500;
}

.pattern-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(255, 196, 0, 0.16);
  color: #ffcc5c;
  font-size: 11px;
  font-weight: 700;
  cursor: help;
}

.confidence-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-bar {
  width: 70px;
  height: 4px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
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
  color: rgba(255, 255, 255, 0.62);
}

.date-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.date-caption {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.42);
}

.tech-tags {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tech-tag {
  display: inline-block;
  width: fit-content;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.78);
  font-size: 11px;
}

.action-merged {
  min-width: 64px;
}

.action-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(41, 98, 255, 0.14);
    color: rgba(255, 255, 255, 0.92);
  }
}

.empty-row {
  padding: 32px 16px;
  text-align: center;
  color: rgba(255, 255, 255, 0.42);
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

@media (max-width: 768px) {
  .patterns-page {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-right {
    width: 100%;
  }

  .date-inputs {
    grid-template-columns: 1fr;
  }

  .results-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
}

.config-modal {
  display: flex;
  flex-direction: column;
  width: 600px;
  max-height: 80vh;
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
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

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
