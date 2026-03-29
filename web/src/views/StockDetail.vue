<template>
  <div class="stock-detail-page">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ t('stock_loading') }}</p>
    </div>

    <template v-else-if="stockInfo">
      <div class="page-header">
        <div class="stock-info">
          <div class="stock-title-row">
            <h1>{{ stockInfo.name }}</h1>
            <span class="stock-code">{{ stockInfo.code }}</span>
            <span class="stock-market">{{ marketLabel }}</span>
          </div>
        </div>
        <div class="price-info" :class="change >= 0 ? 'price-up' : 'price-down'">
          <div class="current-price">
            {{ latestBar?.close?.toFixed(2) || '-' }}
          </div>
          <div class="price-change">
            {{ formatChange(change) }}
            <span class="change-value">({{ changeValue >= 0 ? '+' : '' }}{{ changeValue.toFixed(2) }})</span>
          </div>
        </div>
      </div>

      <div class="content-grid">
        <div class="main-chart">
          <div class="chart-mode-bar">
            <div class="chart-mode-tabs">
              <button
                class="chart-mode-btn"
                :class="{ active: activeChartMode === 'native' }"
                @click="activeChartMode = 'native'"
              >
                {{ t('stock_chart_native') }}
              </button>
              <button
                class="chart-mode-btn"
                :class="{ active: activeChartMode === 'tradingview' }"
                @click="activeChartMode = 'tradingview'"
              >
                {{ t('stock_chart_tv') }}
              </button>
            </div>
            <p class="chart-mode-copy">
              {{
                activeChartMode === 'native'
                  ? t('stock_chart_native_desc')
                  : t('stock_chart_tv_desc')
              }}
            </p>
          </div>

          <div v-if="activeChartMode === 'native'" class="chart-context-bar">
            <div class="context-copy">
              <span class="context-label">{{ t('stock_pattern_range_label') }}</span>
              <strong>{{ patternRangeLabel }}</strong>
            </div>
            <div class="context-actions">
              <button class="context-btn" :class="{ active: showPatternMarks }" @click="showPatternMarks = !showPatternMarks">
                {{ showPatternMarks ? t('stock_pattern_marks_hide') : t('stock_pattern_marks_show') }}
              </button>
              <button class="context-btn" :disabled="!hasRequestedPatternRange" @click="focusRangeRequestId++">
                {{ t('stock_pattern_focus_range') }}
              </button>
            </div>
          </div>
          <KLineChart
            v-if="activeChartMode === 'native'"
            :title="stockInfo.name"
            :data="klineData"
            :loading="loading"
            :adjust="currentAdjust"
            :external-hint="chartHint"
            :show-pattern-marks="showPatternMarks"
            :pattern-marks="chartPatternMarks"
            :highlight-range="chartPatternRange"
            :highlighted-pattern-key="activePatternKey"
            :focus-range-request-id="focusRangeRequestId"
            @adjustChange="handleAdjustChange"
          />
          <TradingViewWidget
            v-else
            :code="stockInfo.code"
            :exchange="stockInfo.exchange"
            theme="dark"
          />
        </div>

        <aside class="side-panel">
          <div class="panel-section">
            <h3>{{ t('stock_profile') }}</h3>
            <div class="profile-grid">
              <div class="profile-item">
                <span class="label">{{ t('stock_open') }}</span>
                <span class="value">{{ latestBar?.open?.toFixed(2) || '-' }}</span>
              </div>
              <div class="profile-item">
                <span class="label">{{ t('stock_high') }}</span>
                <span class="value">{{ latestBar?.high?.toFixed(2) || '-' }}</span>
              </div>
              <div class="profile-item">
                <span class="label">{{ t('stock_low') }}</span>
                <span class="value">{{ latestBar?.low?.toFixed(2) || '-' }}</span>
              </div>
              <div class="profile-item">
                <span class="label">{{ t('label_volume') }}</span>
                <span class="value">{{ formatVolume(latestBar?.vol) }}</span>
              </div>
              <div class="profile-item">
                <span class="label">{{ t('stock_turnover') }}</span>
                <span class="value">{{ formatTurnover(latestBar?.amount) }}</span>
              </div>
              <div class="profile-item">
                <span class="label">{{ t('stock_industry') }}</span>
                <span class="value">{{ stockInfo.industry || '-' }}</span>
              </div>
              <div class="profile-item">
                <span class="label">{{ t('stock_list_date') }}</span>
                <span class="value">{{ stockInfo.list_date || '-' }}</span>
              </div>
            </div>
          </div>

          <div class="panel-section validation-panel">
            <div class="section-header">
              <h3>筛选验证</h3>
              <span v-if="screeningTradeDate" class="section-chip">来自 {{ formatDisplayDate(screeningTradeDate) }} 筛选</span>
            </div>
            <p class="validation-copy">
              结合最新价格、指标和形态数据，帮助复核本次筛选结果是否仍然有效。
            </p>
            <div v-if="freshnessItems.length" class="freshness-grid">
              <div v-for="item in freshnessItems" :key="item.key" class="freshness-item">
                <span class="label">{{ item.label }}</span>
                <div class="freshness-value">
                  <span class="freshness-badge" :class="item.current ? 'is-current' : 'is-stale'">
                    {{ item.current ? '最新' : '待确认' }}
                  </span>
                  <span>{{ formatDisplayDate(item.tradeDate) }}</span>
                </div>
              </div>
            </div>
            <div v-if="validationMetrics.length" class="validation-group">
              <h4>筛选指标</h4>
              <div class="validation-list">
                <div v-for="item in validationMetrics" :key="`${item.metric}-${item.trade_date}`" class="validation-item">
                  <div class="validation-item-header">
                    <strong>{{ item.metric }}</strong>
                    <span>{{ formatDisplayDate(item.trade_date) }}</span>
                  </div>
                  <p>{{ item.summary }}</p>
                </div>
              </div>
            </div>
            <div v-if="validationPatterns.length" class="validation-group">
              <h4>形态注释</h4>
              <div class="validation-list">
                <div v-for="item in validationPatterns" :key="`${item.metric}-${item.trade_date}-${item.summary}`" class="validation-item">
                  <div class="validation-item-header">
                    <strong>{{ item.metric }}</strong>
                    <span>{{ formatDisplayDate(item.trade_date) }}</span>
                  </div>
                  <p>{{ item.summary }}</p>
                </div>
              </div>
            </div>
            <div v-if="!validationMetrics.length && !validationPatterns.length" class="empty-state validation-empty">
              暂无可展示的验证信息
            </div>
          </div>

          <div class="panel-section">
            <h3>{{ t('stock_actions') }}</h3>
            <div class="action-buttons">
              <button class="action-btn primary" @click="goBacktest">
                <span class="btn-icon">⚡</span>
                <span>{{ t('stock_backtest') }}</span>
              </button>
              <button class="action-btn" @click="addToWatchlist">
                <span class="btn-icon">⭐</span>
                <span>{{ inWatchlist ? t('stock_watch_remove') : t('stock_watch_add') }}</span>
              </button>
              <button class="action-btn" @click="analyzePatterns">
                <span class="btn-icon">🔍</span>
                <span>{{ t('stock_analyze_patterns') }}</span>
              </button>
            </div>
          </div>

          <div class="panel-section">
            <div class="section-header">
              <h3>{{ t('stock_related_patterns') }}</h3>
              <span class="section-chip">{{ patternRangeLabel }}</span>
            </div>
            <p v-if="activeChartMode === 'tradingview'" class="pattern-note">
              {{ t('stock_tv_pattern_note') }}
            </p>
            <div v-if="patterns.length > 0" class="pattern-list-meta">
              <span>{{ patterns.length }} {{ t('stock_pattern_records') }}</span>
              <span>{{ t('stock_pattern_link_hint') }}</span>
            </div>
            <div v-if="patterns.length > 0" class="pattern-list">
              <button
                v-for="pattern in patterns"
                :key="pattern.pattern_key"
                class="pattern-item"
                :class="{ active: activePatternKey === pattern.pattern_key }"
                @mouseenter="activePatternKey = pattern.pattern_key"
                @mouseleave="activePatternKey = ''"
                @focus="activePatternKey = pattern.pattern_key"
                @blur="activePatternKey = ''"
                @click="activePatternKey = pattern.pattern_key"
              >
                <div class="pattern-info">
                  <span class="pattern-name">{{ getPatternLabel(pattern.pattern_name) }}</span>
                  <span class="pattern-date">{{ formatDisplayDate(pattern.trade_date) }}</span>
                </div>
                <div class="pattern-meta">
                  <span class="pattern-signal" :class="getSignalClass(pattern.pattern_type)">
                    {{ getSignalText(pattern.pattern_type) }}
                  </span>
                  <span class="pattern-badge">{{ pattern.confidence }}%</span>
                </div>
              </button>
            </div>
            <div v-else class="empty-state">
              {{ t('stock_no_patterns') }}
            </div>
          </div>
        </aside>
      </div>
    </template>

    <div v-else class="error-state">
      <p>{{ t('stock_not_found') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { attentionApi, patternApi, stockApi } from '@/api'
import KLineChart from '@/components/charts/KLineChart.vue'
import TradingViewWidget from '@/components/charts/TradingViewWidget.vue'
import { useLocale } from '@/composables/useLocale'
import { getPatternLabel as resolvePatternLabel } from '@/utils/patternLabels'

interface KlineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
}

interface BarData {
  open?: number
  high?: number
  low?: number
  close?: number
  vol?: number
  amount?: number
}

interface PatternDetail {
  id?: number
  pattern_key: string
  pattern_name: string
  pattern_type: string
  trade_date: string
  confidence: number
}

interface ChartPatternMark {
  key: string
  name: string
  date: string
  confidence: number
  signal: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
}

interface DateRange {
  start: string
  end: string
}

interface ValidationItem {
  metric: string
  trade_date?: string | null
  summary: string
}

const route = useRoute()
const router = useRouter()
const { locale, t } = useLocale()
const loading = ref(false)
const inWatchlist = ref(false)
const activeChartMode = ref<'native' | 'tradingview'>('native')
const showPatternMarks = ref(true)
const activePatternKey = ref('')
const focusRangeRequestId = ref(0)

const stockInfo = ref<any>(null)
const klineData = ref<KlineData[]>([])
const patterns = ref<PatternDetail[]>([])
const currentAdjust = ref<'bfq' | 'qfq' | 'hfq'>('qfq')
const adjustFallbackActive = ref(false)
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')

const code = computed(() => route.params.code as string)
const screeningTradeDate = computed(() => toQueryDate(route.query.screening_date))
const marketLabel = computed(() => {
  const exchange = String(stockInfo.value?.exchange || '').toUpperCase()
  if (exchange === 'SSE' || exchange === 'SH') return t('stock_market_sh')
  if (exchange === 'SZSE' || exchange === 'SZ') return t('stock_market_sz')
  if (exchange === 'BSE' || exchange === 'BJ') return t('stock_market_bj')
  return exchange || '-'
})

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

const shiftCompactDate = (value: string, days: number) => {
  const date = parseDateValue(value)
  if (Number.isNaN(date.getTime())) return value
  date.setDate(date.getDate() + days)
  return formatCompactDate(date)
}

const formatDisplayDate = (value?: string | null) => {
  if (!value) return '-'
  if (value.includes('-')) return value
  if (value.length !== 8) return value
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
}

const toQueryDate = (value: unknown) => {
  if (Array.isArray(value)) return String(value[0] || '').trim()
  return String(value || '').trim()
}

const requestedPatternRange = computed<DateRange | null>(() => {
  const start = toQueryDate(route.query.pattern_start)
  const end = toQueryDate(route.query.pattern_end)

  if (!start && !end) return null
  const normalizedStart = start || end
  const normalizedEnd = end || start
  if (!normalizedStart || !normalizedEnd) return null

  return normalizedStart <= normalizedEnd
    ? { start: normalizedStart, end: normalizedEnd }
    : { start: normalizedEnd, end: normalizedStart }
})

const hasRequestedPatternRange = computed(() => !!requestedPatternRange.value)
const freshnessItems = computed(() => {
  const freshness = stockInfo.value?.data_freshness
  if (!freshness) return []
  return [
    {
      key: 'price',
      label: '价格数据',
      tradeDate: freshness.price_trade_date,
      current: Boolean(freshness.price_current),
    },
    {
      key: 'indicator',
      label: '指标快照',
      tradeDate: freshness.indicator_trade_date,
      current: Boolean(freshness.indicator_current),
    },
    {
      key: 'pattern',
      label: '形态识别',
      tradeDate: freshness.pattern_trade_date,
      current: Boolean(freshness.pattern_current),
    },
  ].filter((item) => item.tradeDate)
})
const validationMetrics = computed<ValidationItem[]>(() => stockInfo.value?.validation_context?.screening_metrics || [])
const validationPatterns = computed<ValidationItem[]>(() => stockInfo.value?.validation_context?.pattern_annotations || [])

const patternRangeLabel = computed(() => {
  if (!requestedPatternRange.value) {
    return t('stock_pattern_range_current')
  }
  return `${formatDisplayDate(requestedPatternRange.value.start)} 至 ${formatDisplayDate(requestedPatternRange.value.end)}`
})

const chartPatternRange = computed(() =>
  requestedPatternRange.value
    ? {
        start: requestedPatternRange.value.start,
        end: requestedPatternRange.value.end,
        label: t('stock_pattern_range_focus'),
      }
    : null
)

const chartPatternMarks = computed<ChartPatternMark[]>(() =>
  patterns.value.map((pattern) => ({
    key: pattern.pattern_key,
    name: getPatternLabel(pattern.pattern_name),
    date: pattern.trade_date,
    confidence: pattern.confidence,
    signal: getSignalType(pattern.pattern_type),
  }))
)

const latestBar = computed<BarData | null>(() => {
  if (klineData.value.length === 0) return null
  const last = klineData.value[klineData.value.length - 1]
  return {
    open: last.open,
    high: last.high,
    low: last.low,
    close: last.close,
    vol: last.volume,
    amount: last.amount,
  }
})

const change = computed(() => {
  if (!latestBar.value) return 0
  return Number(latestBar.value.close) - Number(latestBar.value.open)
})

const changeValue = computed(() => {
  if (!latestBar.value) return 0
  return ((Number(latestBar.value.close) - Number(latestBar.value.open)) / Number(latestBar.value.open)) * 100
})

const chartHint = computed(() => {
  return adjustFallbackActive.value ? t('stock_adjust_fallback') : ''
})

const formatVolume = (volume: number | undefined) => {
  if (!volume) return '-'
  if (volume >= 1000000) return `${(volume / 1000000).toFixed(2)}M`
  if (volume >= 1000) return `${(volume / 1000).toFixed(2)}K`
  return volume.toString()
}

const formatTurnover = (turnover: number | undefined) => {
  if (!turnover) return '-'
  if (turnover >= 1000000000) return `${(turnover / 1000000000).toFixed(2)}B`
  if (turnover >= 1000000) return `${(turnover / 1000000).toFixed(2)}M`
  return `${(turnover / 1000).toFixed(2)}K`
}

const formatChange = (value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`

const getPatternLabel = (name: string) => {
  return resolvePatternLabel(name, locale.value)
}

const getSignalType = (patternType?: string | null): 'BULLISH' | 'BEARISH' | 'NEUTRAL' => {
  const normalized = String(patternType || '').toLowerCase()
  if (normalized === 'reversal' || normalized === 'breakout') return 'BULLISH'
  if (normalized === 'breakdown') return 'BEARISH'
  return 'NEUTRAL'
}

const getSignalText = (patternType?: string | null) => {
  const signal = getSignalType(patternType)
  if (signal === 'BULLISH') return '看涨'
  if (signal === 'BEARISH') return '看跌'
  return '中性'
}

const getSignalClass = (patternType?: string | null) => getSignalType(patternType).toLowerCase()

const getLatestTradeDate = () => formatCompactDate(new Date())

const getDefaultStartDate = () => shiftCompactDate(getLatestTradeDate(), -180)

const getChartWindow = () => {
  if (!requestedPatternRange.value) {
    return {
      start: getDefaultStartDate(),
      end: getLatestTradeDate(),
    }
  }

  return {
    start: shiftCompactDate(requestedPatternRange.value.start, -90),
    end: shiftCompactDate(requestedPatternRange.value.end, 45),
  }
}

const fetchStockDetail = async (
  adjust: 'bfq' | 'qfq' | 'hfq' = currentAdjust.value,
  refreshPatterns = false
) => {
  loading.value = true
  try {
    const chartWindow = getChartWindow()
    const patternWindow = requestedPatternRange.value || chartWindow

    const stockPromise = stockApi.getStockDetail(code.value, {
      start_date: chartWindow.start,
      end_date: chartWindow.end,
      adjust,
    })
    const patternPromise = refreshPatterns
      ? patternApi.getPatterns(code.value, {
          start_date: patternWindow.start,
          end_date: patternWindow.end,
          limit: 200,
        }).catch((error: any) => {
          console.error('获取形态数据失败:', error)
          return []
        })
      : Promise.resolve(patterns.value)

    const [stockData, patternsData] = await Promise.all([stockPromise, patternPromise])

    stockInfo.value = stockData
    adjustFallbackActive.value = stockData?.adjust_note === 'requested_adjust_data_unavailable_fallback_to_bfq'
    patterns.value = (patternsData || [])
      .map((pattern: any, index: number) => ({
        ...pattern,
        trade_date: pattern.trade_date || '',
        confidence: pattern.confidence ? Math.round(Number(pattern.confidence)) : 0,
        pattern_key: `${pattern.pattern_name}-${pattern.trade_date}-${pattern.id || index}`,
      }))
      .sort((a: PatternDetail, b: PatternDetail) => {
        const dateDiff = (b.trade_date || '').localeCompare(a.trade_date || '')
        if (dateDiff !== 0) return dateDiff
        return (b.confidence || 0) - (a.confidence || 0)
      })

    activePatternKey.value = ''
    if (stockData?.bars) {
      klineData.value = stockData.bars.map((bar: any) => ({
        date: bar.trade_date,
        open: Number(bar.open),
        high: Number(bar.high),
        low: Number(bar.low),
        close: Number(bar.close),
        volume: Number(bar.vol),
        amount: Number(bar.amount),
      }))
    } else {
      klineData.value = []
    }

    await syncWatchlistStatus()
  } catch (error) {
    console.error('Failed to fetch stock detail:', error)
  } finally {
    loading.value = false
  }
}

const handleAdjustChange = (adjust: string) => {
  const nextAdjust = (adjust || 'bfq') as 'bfq' | 'qfq' | 'hfq'
  if (nextAdjust === currentAdjust.value) return
  currentAdjust.value = nextAdjust
  fetchStockDetail(nextAdjust)
}

const addToWatchlist = async () => {
  try {
    if (inWatchlist.value) {
      await attentionApi.remove(code.value)
    } else {
      await attentionApi.add(code.value)
    }
    inWatchlist.value = !inWatchlist.value
    showNotification?.('success', inWatchlist.value ? '已添加到关注列表' : '已取消关注')
  } catch (error) {
    console.error('Failed to update watchlist:', error)
    showNotification?.('error', '更新关注状态失败')
  }
}

const analyzePatterns = () => {
  router.push({
    path: '/patterns',
    query: { code: code.value },
  })
}

const goBacktest = () => {
  router.push({ path: '/backtest', query: { code: code.value } })
}

const syncWatchlistStatus = async () => {
  try {
    const list = await attentionApi.getList()
    inWatchlist.value = (list || []).some((item: any) => {
      const raw = item.code || item.symbol || item.ts_code?.split('.')?.[0]
      return raw === code.value
    })
  } catch {
    inWatchlist.value = false
  }
}

watch(
  () => [code.value, route.query.pattern_start, route.query.pattern_end],
  () => {
    fetchStockDetail(currentAdjust.value, true)
  }
)

onMounted(() => {
  fetchStockDetail(currentAdjust.value, true)
})
</script>

<style scoped lang="scss">
.stock-detail-page {
  box-sizing: border-box;
  padding: 24px;
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
  overflow: hidden;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;

  p {
    margin-top: 16px;
    color: rgba(255, 255, 255, 0.6);
  }
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #2962FF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 0;
}

.stock-info {
  min-width: 0;
}

.stock-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;

  h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
  }
}

.stock-code,
.stock-market {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
}

.stock-code {
  font-family: 'JetBrains Mono', monospace;
  color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.05);
}

.stock-market {
  color: rgba(255, 255, 255, 0.56);
  background: rgba(255, 255, 255, 0.03);
}

.price-info {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;

  .current-price {
    font-size: 24px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1;
  }

  .price-change {
    font-size: 13px;
    white-space: nowrap;
  }
}

.price-up {
  color: #00C853;
}

.price-down {
  color: #FF1744;
}

.change-value {
  font-size: 14px;
  opacity: 0.72;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
  min-height: 0;
  overflow: hidden;
}

.main-chart {
  display: flex;
  flex-direction: column;
  background: rgba(26, 26, 26, 0.5);
  border-radius: 12px;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
}

.chart-mode-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
}

.chart-mode-tabs {
  display: flex;
  gap: 8px;
}

.chart-mode-btn {
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: rgba(255, 255, 255, 0.85);
    border-color: rgba(255, 255, 255, 0.24);
  }

  &.active {
    background: rgba(41, 98, 255, 0.16);
    color: #6ab0ff;
    border-color: rgba(41, 98, 255, 0.42);
  }
}

.chart-mode-copy {
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-align: right;
}

.chart-context-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  background:
    linear-gradient(90deg, rgba(41, 98, 255, 0.16), transparent 42%),
    rgba(8, 13, 24, 0.72);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.context-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;

  strong {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.92);
  }
}

.context-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-actions {
  display: flex;
  gap: 8px;
}

.context-btn {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    border-color: rgba(41, 98, 255, 0.52);
    color: rgba(255, 255, 255, 0.92);
  }

  &.active {
    background: rgba(41, 98, 255, 0.14);
    border-color: rgba(41, 98, 255, 0.72);
    color: #a9c0ff;
  }

  &:disabled {
    opacity: 0.38;
    cursor: not-allowed;
  }
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
  min-height: 0;
  overflow: auto;
}

.panel-section {
  padding: 20px;
  background: rgba(26, 26, 26, 0.5);
  border-radius: 12px;

  h3 {
    margin: 0 0 16px;
    font-size: 16px;
    font-weight: 600;
  }
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.section-chip {
  display: inline-flex;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(41, 98, 255, 0.14);
  color: #a9c0ff;
  font-size: 12px;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.validation-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.validation-copy {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.62);
}

.freshness-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.freshness-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);

  .label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.freshness-value {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
}

.freshness-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;

  &.is-current {
    background: rgba(0, 200, 83, 0.15);
    color: #00C853;
  }

  &.is-stale {
    background: rgba(255, 193, 7, 0.15);
    color: #ffd54f;
  }
}

.validation-group {
  display: flex;
  flex-direction: column;
  gap: 10px;

  h4 {
    margin: 0;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.62);
  }
}

.validation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.validation-item {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);

  p {
    margin: 6px 0 0;
    font-size: 13px;
    line-height: 1.45;
    color: rgba(255, 255, 255, 0.72);
  }
}

.validation-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.48);

  strong {
    color: rgba(255, 255, 255, 0.86);
    text-transform: capitalize;
  }
}

.validation-empty {
  padding: 12px;
}

.profile-item {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }

  .value {
    font-size: 14px;
    font-weight: 500;
  }
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  background: transparent;
  color: rgba(255, 255, 255, 0.82);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  &.primary {
    background: rgba(41, 98, 255, 0.15);
    border-color: #2962FF;
    color: #8fb0ff;
  }
}

.pattern-list-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.46);
}

.pattern-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
}

.pattern-note {
  margin: 0 0 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.pattern-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;

  &:hover,
  &.active {
    background: rgba(41, 98, 255, 0.08);
    border-color: rgba(41, 98, 255, 0.34);
  }
}

.pattern-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pattern-name {
  font-size: 13px;
  font-weight: 600;
}

.pattern-date {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.44);
}

.pattern-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.pattern-signal {
  font-size: 11px;
  font-weight: 600;

  &.bullish {
    color: #00C853;
  }

  &.bearish {
    color: #FF1744;
  }

  &.neutral {
    color: rgba(255, 255, 255, 0.62);
  }
}

.pattern-badge {
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.86);
  font-size: 12px;
  font-weight: 600;
}

.empty-state {
  padding: 20px;
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
}

@media (max-width: 1200px) {
  .stock-detail-page {
    height: auto;
    min-height: 100%;
    overflow: auto;
  }

  .content-grid {
    grid-template-columns: 1fr;
    overflow: visible;
  }

  .side-panel {
    flex-direction: row;
    flex-wrap: wrap;
    overflow: visible;
  }

  .panel-section {
    flex: 1;
    min-width: 280px;
  }
}

@media (max-width: 768px) {
  .stock-detail-page {
    padding: 16px;
    gap: 16px;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .price-info {
    align-items: baseline;
  }

  .chart-mode-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .chart-mode-copy {
    text-align: left;
  }

  .chart-context-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .context-actions {
    flex-wrap: wrap;
  }

  .side-panel {
    flex-direction: column;
  }

  .panel-section {
    min-width: auto;
  }

  .profile-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .stock-title-row h1 {
    font-size: 18px;
  }

  .price-info {
    gap: 8px;

    .current-price {
      font-size: 20px;
    }

    .price-change {
      font-size: 12px;
    }
  }
}
</style>
