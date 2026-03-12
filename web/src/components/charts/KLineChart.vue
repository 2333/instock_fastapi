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
import { ref, computed, watch, onMounted, onUnmounted, shallowRef } from 'vue'
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

interface Props {
  title?: string
  data?: KlineData[]
  loading?: boolean
  showVolume?: boolean
  showPatternMarks?: boolean
  adjust?: 'bfq' | 'qfq' | 'hfq'
  externalHint?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '',
  loading: false,
  showVolume: true,
  showPatternMarks: true,
  adjust: 'bfq',
  externalHint: '',
})
const { t } = useLocale()

const chartRef = ref<HTMLDivElement>()
const chartInstance = shallowRef<any>(null)
const selectedPeriod = ref('day')
const selectedAdjust = ref('bfq')
const activeIndicators = ref<string[]>([])
const noDataText = ref('')
const hintText = ref('')

const periods = [
  { label: '1分', value: '1min' },
  { label: '5分', value: '5min' },
  { label: '15分', value: '15min' },
  { label: '日', value: 'day' },
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
]

const adjustTypes = [
  { label: '不复权', value: 'bfq' },
  { label: '前复权', value: 'qfq' },
  { label: '后复权', value: 'hfq' },
]

const availableIndicators = [
  { key: 'ma', label: 'MA' },
  { key: 'ema', label: 'EMA' },
  { key: 'macd', label: 'MACD' },
  { key: 'kdj', label: 'KDJ' },
  { key: 'rsi', label: 'RSI' },
  { key: 'boll', label: 'BOLL' },
]

const chartTitle = computed(() => props.title || t('kline_default_title'))

const currentPrice = computed(() => {
  if (!displayData.value || displayData.value.length === 0) return null
  return displayData.value[displayData.value.length - 1].close
})

const priceChange = computed(() => {
  if (!displayData.value || displayData.value.length < 2) return 0
  const current = displayData.value[displayData.value.length - 1].close
  const previous = displayData.value[displayData.value.length - 2].close
  return ((current - previous) / previous) * 100
})

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

const calculateMA = (data: KlineData[], period: number): (number | null)[] => {
  const result: (number | null)[] = []
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

const calculateEMA = (data: KlineData[], period: number): (number | null)[] => {
  const result: (number | null)[] = []
  if (data.length === 0) return result
  const multiplier = 2 / (period + 1)
  let prevEma: number | null = null

  for (let i = 0; i < data.length; i++) {
    const close = data[i].close
    if (i < period - 1) {
      result.push(null)
      continue
    }
    if (prevEma === null) {
      const base = data.slice(i - period + 1, i + 1).reduce((sum, item) => sum + item.close, 0) / period
      prevEma = base
      result.push(base)
      continue
    }
    const emaValue: number = (close - prevEma) * multiplier + prevEma
    prevEma = emaValue
    result.push(emaValue)
  }

  return result
}

const calculateBOLL = (data: KlineData[], period = 20, stdMult = 2): { upper: (number | null)[], mid: (number | null)[], lower: (number | null)[] } => {
  const upper: (number | null)[] = []
  const mid: (number | null)[] = []
  const lower: (number | null)[] = []
  
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      upper.push(null)
      mid.push(null)
      lower.push(null)
    } else {
      const sliced = data.slice(i - period + 1, i + 1)
      const closes = sliced.map(d => d.close)
      const midValue = closes.reduce((a, b) => a + b, 0) / period
      mid.push(midValue)
      
      const variance = closes.reduce((sum, val) => sum + Math.pow(val - midValue, 2), 0) / period
      const std = Math.sqrt(variance)
      
      upper.push(midValue + stdMult * std)
      lower.push(midValue - stdMult * std)
    }
  }
  return { upper, mid, lower }
}

const parseDate = (value: string) => {
  if (!value) return new Date(NaN)
  if (value.includes('-')) return new Date(value)
  const y = Number(value.slice(0, 4))
  const m = Number(value.slice(4, 6)) - 1
  const d = Number(value.slice(6, 8))
  return new Date(y, m, d)
}

const formatDate = (date: Date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
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
    const dt = parseDate(item.date)
    if (Number.isNaN(dt.getTime())) continue
    const key = mode === 'week'
      ? getWeekKey(dt)
      : `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(item)
  }

  const result: KlineData[] = []
  for (const [, items] of groups) {
    if (items.length === 0) continue
    const sorted = [...items].sort((a, b) => parseDate(a.date).getTime() - parseDate(b.date).getTime())
    const first = sorted[0]
    const last = sorted[sorted.length - 1]
    result.push({
      date: formatDate(parseDate(last.date)),
      open: first.open,
      high: Math.max(...sorted.map((x) => x.high)),
      low: Math.min(...sorted.map((x) => x.low)),
      close: last.close,
      volume: sorted.reduce((sum, x) => sum + (x.volume || 0), 0),
      amount: sorted.reduce((sum, x) => sum + (x.amount || 0), 0),
    })
  }
  return result.sort((a, b) => parseDate(a.date).getTime() - parseDate(b.date).getTime())
}

const displayData = computed(() => {
  const raw = props.data || []
  if (raw.length === 0) {
    const adjustLabelMap: Record<string, string> = {
      bfq: '不复权',
      qfq: '前复权',
      hfq: '后复权',
    }
    noDataText.value = `暂无${adjustLabelMap[selectedAdjust.value] || ''}K线数据`
    return []
  }

  noDataText.value = ''

  if (selectedPeriod.value === 'day') return raw
  if (selectedPeriod.value === 'week') return aggregateBars(raw, 'week')
  if (selectedPeriod.value === 'month') return aggregateBars(raw, 'month')

  noDataText.value = `暂无${selectedPeriod.value}级别数据`
  return []
})

const unsupportedIndicators = computed(() =>
  activeIndicators.value.filter((key) => ['macd', 'kdj', 'rsi'].includes(key))
)

watch([unsupportedIndicators, () => props.externalHint], () => {
  const hints: string[] = []
  if (unsupportedIndicators.value.length > 0) {
    hints.push(`${unsupportedIndicators.value.map((x) => x.toUpperCase()).join('/')} 暂未接入`)
  }
  if (props.externalHint) {
    hints.push(props.externalHint)
  }
  hintText.value = hints.join('；')
}, { immediate: true })

const effectiveIndicatorSet = computed(() =>
  activeIndicators.value.filter((key) => !unsupportedIndicators.value.includes(key))
)

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
  const dates = data.map(d => d.date)
  const opens = data.map(d => d.open)
  const closes = data.map(d => d.close)
  const lows = data.map(d => d.low)
  const highs = data.map(d => d.high)
  const volumes = data.map(d => d.volume)

  const isUp = closes.map((close, i) => close >= opens[i])

  const candlestickData = data.map((d) => [
    d.open,
    d.close,
    d.low,
    d.high,
  ])

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

  if (props.showVolume) {
    const volumeData = volumes
    series.push({
      type: 'bar',
      name: 'Volume',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: volumeData,
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
        const kline = data[dataIndex]
        let html = `<div style="font-weight: 600; margin-bottom: 8px;">${kline.date}</div>`
        html += `<div>${t('label_open')}: <span style="color: ${opens[dataIndex] <= closes[dataIndex] ? '#00C853' : '#FF1744'}">${opens[dataIndex].toFixed(2)}</span></div>`
        html += `<div>${t('label_high')}: <span style="color: #FF9800">${highs[dataIndex].toFixed(2)}</span></div>`
        html += `<div>${t('label_low')}: <span style="color: #2196F3">${lows[dataIndex].toFixed(2)}</span></div>`
        html += `<div>${t('label_close')}: <span style="color: ${opens[dataIndex] <= closes[dataIndex] ? '#00C853' : '#FF1744'}">${closes[dataIndex].toFixed(2)}</span></div>`
        html += `<div>${t('label_volume')}: <span style="color: #E91E63">${(volumes[dataIndex] / 10000).toFixed(2)}万</span></div>`
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
        axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
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
      { type: 'slider', xAxisIndex: [0, 1], start: 50, end: 100, height: 20, bottom: 0, borderColor: 'rgba(255, 255, 255, 0.1)', fillerColor: 'rgba(41, 98, 255, 0.2)', handleStyle: { color: '#2962FF' } },
    ],
    series,
  }

  chartInstance.value.setOption(option)
}

const emit = defineEmits<{
  (e: 'periodChange', value: string): void
  (e: 'adjustChange', value: string): void
  (e: 'click', data: KlineData): void
}>()

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
  height: 100%;
  min-height: 400px;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(26, 26, 26, 0.5);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.chart-title {
  display: flex;
  align-items: center;
  gap: 12px;

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
  gap: 16px;
}

.period-selector,
.adjust-selector,
.indicator-toggles {
  display: flex;
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
  height: calc(100% - 52px);
  min-height: 348px;
}

.chart-hint {
  position: absolute;
  left: 16px;
  right: 16px;
  top: 60px;
  z-index: 3;
  color: rgba(255, 196, 0, 0.92);
  font-size: 12px;
  pointer-events: none;
}

.chart-empty {
  position: absolute;
  inset: 52px 0 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
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
  to { transform: rotate(360deg); }
}
</style>
