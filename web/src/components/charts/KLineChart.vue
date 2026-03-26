<template>
  <div class="kline-chart">
    <div class="chart-header">
      <div class="chart-title">
        <h3>{{ chartTitle }}</h3>
        <span v-if="currentPrice" class="current-price" :class="priceChange >= 0 ? 'price-up' : 'price-down'">
          {{ currentPrice.toFixed(2) }}
          <span class="price-change">{{ priceChange >= 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}%</span>
        </span>
      </div>
      <div class="chart-controls">
        <div class="period-selector">
          <button
            v-for="period in periods"
            :key="period.value"
            class="period-btn"
            :class="{ active: selectedPeriod === period.value }"
            @click="setPeriod(period.value)"
          >
            {{ period.label }}
          </button>
        </div>
        <div class="adjust-selector">
          <button
            v-for="adjust in adjustTypes"
            :key="adjust.value"
            class="adjust-btn"
            :class="{ active: selectedAdjust === adjust.value }"
            @click="setAdjust(adjust.value)"
          >
            {{ adjust.label }}
          </button>
        </div>
        <div class="indicator-toggles">
          <button
            v-for="indicator in availableIndicators"
            :key="indicator.key"
            class="indicator-btn"
            :class="{ active: activeIndicators.includes(indicator.key) }"
            @click="toggleIndicator(indicator.key)"
          >
            {{ indicator.label }}
          </button>
        </div>
      </div>
    </div>
    <div ref="chartRef" class="chart-container"></div>
    <div v-if="hintText" class="chart-hint">{{ hintText }}</div>
    <div v-if="noDataText" class="chart-empty">{{ noDataText }}</div>
    <div v-if="loading" class="chart-loading">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { useResizeObserver } from '@vueuse/core'
import { useLocale } from '@/composables/useLocale'

interface KlineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
}

interface PatternMark {
  key: string
  name: string
  date: string
  confidence?: number
  signal?: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
}

interface HighlightRange {
  start: string
  end: string
  label?: string
}

interface Props {
  title?: string
  data?: KlineData[]
  loading?: boolean
  showVolume?: boolean
  showPatternMarks?: boolean
  adjust?: 'bfq' | 'qfq' | 'hfq'
  externalHint?: string
  patternMarks?: PatternMark[]
  highlightedPatternKey?: string
  highlightRange?: HighlightRange | null
  focusRangeRequestId?: number
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  loading: false,
  showVolume: true,
  showPatternMarks: true,
  adjust: 'bfq',
  externalHint: '',
  patternMarks: () => [],
  highlightedPatternKey: '',
  highlightRange: null,
  focusRangeRequestId: 0,
})

const emit = defineEmits<{
  (e: 'periodChange', value: string): void
  (e: 'adjustChange', value: string): void
  (e: 'click', data: KlineData): void
}>()

const { t } = useLocale()

const chartRef = ref<HTMLDivElement>()
const chartInstance = shallowRef<any>(null)
const selectedPeriod = ref('day')
const selectedAdjust = ref('bfq')
const activeIndicators = ref<string[]>([])
const noDataText = ref('')
const hintText = ref('')

const periods = computed(() => [
  { label: t('period_1min'), value: '1min' },
  { label: t('period_5min'), value: '5min' },
  { label: t('period_15min'), value: '15min' },
  { label: t('period_day'), value: 'day' },
  { label: t('period_week'), value: 'week' },
  { label: t('period_month'), value: 'month' },
])

const adjustTypes = computed(() => [
  { label: t('adjust_bfq'), value: 'bfq' },
  { label: t('adjust_qfq'), value: 'qfq' },
  { label: t('adjust_hfq'), value: 'hfq' },
])

const availableIndicators = [
  { key: 'ma', label: 'MA' },
  { key: 'ema', label: 'EMA' },
  { key: 'macd', label: 'MACD' },
  { key: 'kdj', label: 'KDJ' },
  { key: 'rsi', label: 'RSI' },
  { key: 'boll', label: 'BOLL' },
]

const parseDateValue = (value?: string | null): Date => {
  if (!value) return new Date(NaN)
  if (value.includes('-')) return new Date(`${value}T00:00:00`)
  const year = Number(value.slice(0, 4))
  const month = Number(value.slice(4, 6)) - 1
  const day = Number(value.slice(6, 8))
  return new Date(year, month, day)
}

const formatDate = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const formatAxisDate = (value: string) => {
  if (!value) return ''
  const normalized = value.includes('-') ? value : formatDate(parseDateValue(value))
  return normalized.slice(5)
}

const getWeekKey = (date: Date) => {
  const copy = new Date(date)
  const day = copy.getDay() || 7
  copy.setDate(copy.getDate() + 4 - day)
  const yearStart = new Date(copy.getFullYear(), 0, 1)
  const week = Math.ceil((((copy.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
  return `${copy.getFullYear()}-W${String(week).padStart(2, '0')}`
}

const aggregateBars = (data: KlineData[], mode: 'week' | 'month') => {
  const groups = new Map<string, KlineData[]>()
  for (const item of data) {
    const date = parseDateValue(item.date)
    if (Number.isNaN(date.getTime())) continue
    const key = mode === 'week'
      ? getWeekKey(date)
      : `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(item)
  }

  const result: KlineData[] = []
  for (const [, items] of groups) {
    if (items.length === 0) continue
    const sorted = [...items].sort((a, b) => parseDateValue(a.date).getTime() - parseDateValue(b.date).getTime())
    const first = sorted[0]
    const last = sorted[sorted.length - 1]
    result.push({
      date: formatDate(parseDateValue(last.date)),
      open: first.open,
      high: Math.max(...sorted.map((item) => item.high)),
      low: Math.min(...sorted.map((item) => item.low)),
      close: last.close,
      volume: sorted.reduce((sum, item) => sum + (item.volume || 0), 0),
      amount: sorted.reduce((sum, item) => sum + (item.amount || 0), 0),
    })
  }
  return result.sort((a, b) => parseDateValue(a.date).getTime() - parseDateValue(b.date).getTime())
}

const normalizedRawData = computed(() =>
  (props.data || []).map((item) => ({
    ...item,
    date: formatDate(parseDateValue(item.date)),
  }))
)

const displayData = computed(() => {
  const raw = normalizedRawData.value
  if (raw.length === 0) {
    const adjustLabelMap: Record<string, string> = {
      bfq: t('adjust_bfq'),
      qfq: t('adjust_qfq'),
      hfq: t('adjust_hfq'),
    }
    noDataText.value = `${t('no_data_prefix')}${adjustLabelMap[selectedAdjust.value] || ''}${t('no_data_suffix')}`
    return []
  }

  noDataText.value = ''

  if (selectedPeriod.value === 'day') return raw
  if (selectedPeriod.value === 'week') return aggregateBars(raw, 'week')
  if (selectedPeriod.value === 'month') return aggregateBars(raw, 'month')

  noDataText.value = `${t('no_data_prefix')} ${getPeriodLabel(selectedPeriod.value)} ${t('no_period_data_suffix')}`
  return []
})

const chartTitle = computed(() => props.title || t('kline_default_title'))
const getPeriodLabel = (value: string) => {
  return periods.value.find((period) => period.value === value)?.label || value
}

const currentPrice = computed(() => {
  if (displayData.value.length === 0) return null
  return displayData.value[displayData.value.length - 1].close
})

const priceChange = computed(() => {
  if (displayData.value.length < 2) return 0
  const current = displayData.value[displayData.value.length - 1].close
  const previous = displayData.value[displayData.value.length - 2].close
  return ((current - previous) / previous) * 100
})

const unsupportedIndicators = computed(() =>
  activeIndicators.value.filter((key) => ['macd', 'kdj', 'rsi'].includes(key))
)

const effectiveIndicatorSet = computed(() =>
  activeIndicators.value.filter((key) => !unsupportedIndicators.value.includes(key))
)

const resolvePatternDataIndex = (patternDate: string, data: KlineData[]) => {
  const target = formatDate(parseDateValue(patternDate))
  if (!target) return -1

  if (selectedPeriod.value === 'day') {
    return data.findIndex((item) => item.date === target)
  }

  const targetDate = parseDateValue(target)
  const key = selectedPeriod.value === 'week'
    ? getWeekKey(targetDate)
    : `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, '0')}`

  return data.findIndex((item) => {
    const itemDate = parseDateValue(item.date)
    const itemKey = selectedPeriod.value === 'week'
      ? getWeekKey(itemDate)
      : `${itemDate.getFullYear()}-${String(itemDate.getMonth() + 1).padStart(2, '0')}`
    return itemKey === key
  })
}

const resolvedPatternMarks = computed(() => {
  const signalColors: Record<string, string> = {
    BULLISH: '#00C853',
    BEARISH: '#FF1744',
    NEUTRAL: '#FFD54F',
  }

  return (props.patternMarks || [])
    .map((pattern) => {
      const dataIndex = resolvePatternDataIndex(pattern.date, displayData.value)
      if (dataIndex < 0) return null
      const candle = displayData.value[dataIndex]
      const isActive = pattern.key === props.highlightedPatternKey
      return {
        key: pattern.key,
        dataIndex,
        markPoint: {
          coord: [candle.date, candle.high * 1.02],
          value: pattern.name,
          name: pattern.name,
          itemStyle: {
            color: isActive ? '#FFE082' : signalColors[pattern.signal || 'NEUTRAL'],
            borderColor: isActive ? '#FFE082' : signalColors[pattern.signal || 'NEUTRAL'],
          },
          label: { show: false },
          symbol: isActive ? 'diamond' : 'pin',
          symbolSize: isActive ? 24 : 18,
        },
        meta: pattern,
      }
    })
    .filter(Boolean) as Array<{
      key: string
      dataIndex: number
      markPoint: Record<string, unknown>
      meta: PatternMark
    }>
})

const patternTooltipMap = computed(() => {
  const map = new Map<string, PatternMark[]>()
  for (const item of resolvedPatternMarks.value) {
    const key = displayData.value[item.dataIndex]?.date
    if (!key) continue
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(item.meta)
  }
  return map
})

const getHighlightRangeBounds = () => {
  if (!props.highlightRange || displayData.value.length === 0) return null

  const startDate = parseDateValue(props.highlightRange.start)
  const endDate = parseDateValue(props.highlightRange.end)
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return null

  let startIndex = -1
  let endIndex = -1

  displayData.value.forEach((item, index) => {
    const itemDate = parseDateValue(item.date)
    if (startIndex === -1 && itemDate.getTime() >= startDate.getTime()) {
      startIndex = index
    }
    if (itemDate.getTime() <= endDate.getTime()) {
      endIndex = index
    }
  })

  if (startIndex === -1) startIndex = 0
  if (endIndex === -1) endIndex = displayData.value.length - 1
  if (endIndex < startIndex) endIndex = startIndex

  return {
    startIndex,
    endIndex,
    startLabel: displayData.value[startIndex]?.date,
    endLabel: displayData.value[endIndex]?.date,
  }
}

const calculateMA = (data: KlineData[], period: number): Array<number | null> => {
  const result: Array<number | null> = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += data[i - j].close
      }
      result.push(sum / period)
    }
  }
  return result
}

const calculateEMA = (data: KlineData[], period: number): Array<number | null> => {
  const result: Array<number | null> = []
  if (data.length === 0) return result

  const multiplier = 2 / (period + 1)
  let previousEma: number | null = null

  for (let i = 0; i < data.length; i++) {
    const close = data[i].close
    if (i < period - 1) {
      result.push(null)
      continue
    }
    if (previousEma === null) {
      const base = data.slice(i - period + 1, i + 1).reduce((sum, item) => sum + item.close, 0) / period
      previousEma = base
      result.push(base)
      continue
    }
    const emaValue: number = (close - previousEma) * multiplier + previousEma
    previousEma = emaValue
    result.push(emaValue)
  }

  return result
}

const calculateBOLL = (
  data: KlineData[],
  period = 20,
  stdMult = 2
): { upper: Array<number | null>, mid: Array<number | null>, lower: Array<number | null> } => {
  const upper: Array<number | null> = []
  const mid: Array<number | null> = []
  const lower: Array<number | null> = []

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      upper.push(null)
      mid.push(null)
      lower.push(null)
    } else {
      const sliced = data.slice(i - period + 1, i + 1)
      const closes = sliced.map((item) => item.close)
      const midValue = closes.reduce((sum, value) => sum + value, 0) / period
      mid.push(midValue)

      const variance = closes.reduce((sum, value) => sum + Math.pow(value - midValue, 2), 0) / period
      const std = Math.sqrt(variance)
      upper.push(midValue + stdMult * std)
      lower.push(midValue - stdMult * std)
    }
  }

  return { upper, mid, lower }
}

const setPeriod = (period: string) => {
  selectedPeriod.value = period
  emit('periodChange', period)
  updateChart()
}

const setAdjust = (adjust: string) => {
  selectedAdjust.value = adjust
  emit('adjustChange', adjust)
  updateChart()
}

const toggleIndicator = (indicator: string) => {
  const index = activeIndicators.value.indexOf(indicator)
  if (index > -1) {
    activeIndicators.value.splice(index, 1)
  } else {
    activeIndicators.value.push(indicator)
  }
  updateChart()
}

const syncHighlightTip = () => {
  if (!chartInstance.value) return
  if (!props.highlightedPatternKey) {
    chartInstance.value.dispatchAction({ type: 'hideTip' })
    return
  }
  const active = resolvedPatternMarks.value.find((item) => item.key === props.highlightedPatternKey)
  if (!active) return
  chartInstance.value.dispatchAction({
    type: 'showTip',
    seriesIndex: 0,
    dataIndex: active.dataIndex,
  })
}

const focusRange = () => {
  if (!chartInstance.value) return
  const bounds = getHighlightRangeBounds()
  if (!bounds) return
  const startIndex = Math.max(bounds.startIndex - 5, 0)
  const endIndex = Math.min(bounds.endIndex + 5, displayData.value.length - 1)
  chartInstance.value.dispatchAction({
    type: 'dataZoom',
    startValue: displayData.value[startIndex]?.date,
    endValue: displayData.value[endIndex]?.date,
  })
}
const initChart = async () => {
  if (!chartRef.value) return

  const echarts = await import('echarts')
  chartInstance.value = echarts.init(chartRef.value, 'dark', {
    renderer: 'canvas',
    useDirtyRect: true,
  })

  updateChart()

  useResizeObserver(chartRef, () => {
    chartInstance.value?.resize()
  })
}

const updateChart = () => {
  if (!chartInstance.value) return

  const data = displayData.value
  if (!data || data.length === 0) {
    chartInstance.value.clear()
    return
  }

  const dates = data.map((item) => item.date)
  const opens = data.map((item) => item.open)
  const closes = data.map((item) => item.close)
  const lows = data.map((item) => item.low)
  const highs = data.map((item) => item.high)
  const volumes = data.map((item) => item.volume)
  const isUp = closes.map((close, index) => close >= opens[index])
  const candlestickData = data.map((item) => [item.open, item.close, item.low, item.high])

  const series: any[] = [
    {
      type: 'candlestick',
      name: 'K',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: candlestickData,
      barMaxWidth: 16,
      barMinWidth: 5,
      itemStyle: {
        color: '#00C853',
        color0: '#FF1744',
        borderColor: '#00C853',
        borderColor0: '#FF1744',
      },
    },
  ]

  if (effectiveIndicatorSet.value.includes('ma')) {
    const ma5 = calculateMA(data, 5)
    const ma10 = calculateMA(data, 10)
    const ma20 = calculateMA(data, 20)
    const ma60 = calculateMA(data, 60)

    series.push(
      { type: 'line', name: 'MA5', xAxisIndex: 0, yAxisIndex: 0, data: ma5, lineStyle: { color: '#FF9800', width: 1 }, smooth: true },
      { type: 'line', name: 'MA10', xAxisIndex: 0, yAxisIndex: 0, data: ma10, lineStyle: { color: '#2196F3', width: 1 }, smooth: true },
      { type: 'line', name: 'MA20', xAxisIndex: 0, yAxisIndex: 0, data: ma20, lineStyle: { color: '#9C27B0', width: 1 }, smooth: true },
      { type: 'line', name: 'MA60', xAxisIndex: 0, yAxisIndex: 0, data: ma60, lineStyle: { color: '#FF5722', width: 1 }, smooth: true },
    )
  }

  if (effectiveIndicatorSet.value.includes('ema')) {
    const ema12 = calculateEMA(data, 12)
    const ema26 = calculateEMA(data, 26)
    series.push(
      { type: 'line', name: 'EMA12', xAxisIndex: 0, yAxisIndex: 0, data: ema12, lineStyle: { color: '#26C6DA', width: 1 }, smooth: true },
      { type: 'line', name: 'EMA26', xAxisIndex: 0, yAxisIndex: 0, data: ema26, lineStyle: { color: '#AB47BC', width: 1 }, smooth: true },
    )
  }

  if (effectiveIndicatorSet.value.includes('boll')) {
    const boll = calculateBOLL(data)
    series.push(
      { type: 'line', name: 'BOLL_UPPER', xAxisIndex: 0, yAxisIndex: 0, data: boll.upper, lineStyle: { color: 'rgba(255, 255, 255, 0.3)', width: 1, type: 'dashed' }, smooth: true },
      { type: 'line', name: 'BOLL_MID', xAxisIndex: 0, yAxisIndex: 0, data: boll.mid, lineStyle: { color: '#E91E63', width: 1 }, smooth: true },
      { type: 'line', name: 'BOLL_LOWER', xAxisIndex: 0, yAxisIndex: 0, data: boll.lower, lineStyle: { color: 'rgba(255, 255, 255, 0.3)', width: 1, type: 'dashed' }, smooth: true },
    )
  }

  if (props.showPatternMarks && resolvedPatternMarks.value.length > 0) {
    const bounds = getHighlightRangeBounds()
    const candleSeries = series[0]
    candleSeries.markPoint = {
      symbolKeepAspect: true,
      animation: false,
      data: resolvedPatternMarks.value.map((item) => item.markPoint),
    }
    if (bounds?.startLabel && bounds?.endLabel) {
      candleSeries.markArea = {
        silent: true,
        animation: false,
        label: {
          show: true,
          color: 'rgba(255, 255, 255, 0.72)',
          fontSize: 11,
          formatter: props.highlightRange?.label || '评估区间',
        },
        itemStyle: {
          color: 'rgba(41, 98, 255, 0.08)',
          borderColor: 'rgba(41, 98, 255, 0.28)',
          borderWidth: 1,
        },
        data: [
          [
            { xAxis: bounds.startLabel, name: props.highlightRange?.label || '评估区间' },
            { xAxis: bounds.endLabel },
          ],
        ],
      }
    }
  } else if (props.highlightRange) {
    const bounds = getHighlightRangeBounds()
    if (bounds?.startLabel && bounds?.endLabel) {
      series[0].markArea = {
        silent: true,
        animation: false,
        label: {
          show: true,
          color: 'rgba(255, 255, 255, 0.72)',
          fontSize: 11,
          formatter: props.highlightRange.label || '评估区间',
        },
        itemStyle: {
          color: 'rgba(41, 98, 255, 0.08)',
          borderColor: 'rgba(41, 98, 255, 0.28)',
          borderWidth: 1,
        },
        data: [
          [
            { xAxis: bounds.startLabel, name: props.highlightRange.label || '评估区间' },
            { xAxis: bounds.endLabel },
          ],
        ],
      }
    }
  }

  if (props.showVolume) {
    series.push({
      type: 'bar',
      name: 'Volume',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: volumes,
      itemStyle: {
        color: (params: any) => (isUp[params.dataIndex] ? 'rgba(0, 200, 83, 0.6)' : 'rgba(255, 23, 68, 0.6)'),
      },
    })
  }

  const option = {
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 300,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985',
        },
      },
      backgroundColor: 'rgba(26, 26, 26, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: {
        color: 'rgba(255, 255, 255, 0.9)',
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const dataIndex = params[0].dataIndex
        const candle = data[dataIndex]
        let html = `<div style="font-weight: 600; margin-bottom: 8px;">${candle.date}</div>`
        html += `<div>${t('label_open')}: <span style="color: ${opens[dataIndex] <= closes[dataIndex] ? '#00C853' : '#FF1744'}">${opens[dataIndex].toFixed(2)}</span></div>`
        html += `<div>${t('label_high')}: <span style="color: #FF9800">${highs[dataIndex].toFixed(2)}</span></div>`
        html += `<div>${t('label_low')}: <span style="color: #2196F3">${lows[dataIndex].toFixed(2)}</span></div>`
        html += `<div>${t('label_close')}: <span style="color: ${opens[dataIndex] <= closes[dataIndex] ? '#00C853' : '#FF1744'}">${closes[dataIndex].toFixed(2)}</span></div>`
        html += `<div>${t('label_volume')}: <span style="color: #E91E63">${(volumes[dataIndex] / 10000).toFixed(2)}万</span></div>`

        const patternItems = patternTooltipMap.value.get(candle.date) || []
        if (patternItems.length > 0) {
          html += '<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.12);">'
          html += '<div style="margin-bottom: 4px; color: rgba(255,255,255,0.72);">形态标记</div>'
          html += patternItems
            .slice(0, 4)
            .map((item) => `<div>${item.name} · ${Math.round(Number(item.confidence || 0))}%</div>`)
            .join('')
          if (patternItems.length > 4) {
            html += `<div>还有 ${patternItems.length - 4} 个形态</div>`
          }
          html += '</div>'
        }
        return html
      },
    },
    grid: [
      { left: 60, right: 20, top: 40, height: props.showVolume ? '55%' : '80%' },
      { left: 60, right: 20, top: props.showVolume ? '70%' : '85%', height: '15%' },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
        axisLabel: {
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: 10,
          formatter: (value: string) => formatAxisDate(value),
        },
        splitLine: { show: false },
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        boundaryGap: true,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
    ],
    yAxis: [
      {
        scale: true,
        splitArea: { show: true, areaStyle: { color: ['rgba(255, 255, 255, 0.02)', 'rgba(255, 255, 255, 0.05)'] } },
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
        axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
      },
      {
        scale: true,
        gridIndex: 1,
        axisLabel: { show: false },
        axisLine: { show: false },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 50, end: 100 },
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        start: 50,
        end: 100,
        height: 20,
        bottom: 0,
        borderColor: 'rgba(255, 255, 255, 0.1)',
        fillerColor: 'rgba(41, 98, 255, 0.2)',
        handleStyle: { color: '#2962FF' },
      },
    ],
    series,
  }

  chartInstance.value.setOption(option, true)
  syncHighlightTip()
}

watch([unsupportedIndicators, () => props.externalHint], () => {
  const hints: string[] = []
  if (unsupportedIndicators.value.length > 0) {
    hints.push(`${unsupportedIndicators.value.map((item) => item.toUpperCase()).join('/')} ${t('hint_not_available')}`)
  }
  if (props.externalHint) {
    hints.push(props.externalHint)
  }
  hintText.value = hints.join('；')
}, { immediate: true })

watch(() => props.data, () => {
  updateChart()
}, { deep: true })

watch(() => t('label_open'), () => {
  updateChart()
})

watch(() => props.loading, (loading) => {
  if (!loading) {
    setTimeout(updateChart, 100)
  }
})

watch(selectedPeriod, () => {
  updateChart()
})

watch(selectedAdjust, () => {
  updateChart()
})

watch(
  () => props.adjust,
  (adjust) => {
    if (!adjust) return
    selectedAdjust.value = adjust
  },
  { immediate: true }
)

watch(
  () => [props.patternMarks, props.showPatternMarks, props.highlightRange, props.highlightedPatternKey],
  () => {
    updateChart()
  },
  { deep: true }
)

watch(
  () => props.focusRangeRequestId,
  (next, previous) => {
    if (!next || next === previous) return
    focusRange()
  }
)

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  chartInstance.value?.dispose()
})
</script>

<style scoped lang="scss">
.kline-chart {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(26, 26, 26, 0.5);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.chart-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  min-width: 0;

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
}

.current-price {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 20px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.price-change {
  font-size: 14px;
  font-weight: 500;
}

.chart-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex: 1;
  flex-wrap: wrap;
  gap: 16px;
  min-width: 0;
}

.period-selector,
.adjust-selector,
.indicator-toggles {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.period-btn,
.adjust-btn,
.indicator-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.8);
  }

  &.active {
    background: rgba(41, 98, 255, 0.15);
    color: #2962FF;
  }
}

.indicator-btn.active {
  background: rgba(0, 200, 83, 0.15);
  color: #00C853;
}

.chart-container {
  flex: 1;
  min-height: 260px;
}

.chart-hint {
  position: absolute;
  top: 60px;
  left: 16px;
  right: 16px;
  z-index: 3;
  font-size: 12px;
  color: rgba(255, 196, 0, 0.92);
  pointer-events: none;
}

.chart-empty {
  position: absolute;
  inset: 52px 0 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  pointer-events: none;
}

.chart-loading {
  position: absolute;
  inset: 52px 0 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(13, 13, 13, 0.8);
}

.loading-spinner {
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

@media (max-width: 960px) {
  .chart-controls {
    justify-content: flex-start;
  }

  .current-price {
    font-size: 18px;
  }

  .chart-container {
    min-height: 220px;
  }
}
</style>
