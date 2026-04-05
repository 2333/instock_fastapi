<template>
  <div class="report-detail-page">
    <div class="page-header">
      <div class="header-left">
        <button class="btn btn-secondary btn-small" @click="goBack">← 返回</button>
        <div>
          <h1>{{ report?.title }}</h1>
          <p class="subtitle">
            {{ typeLabels[report?.type] }} · 生成于 {{ formatDate(report?.generated_at) }}
            <span v-if="report?.data_date">· 数据日期：{{ report.data_date }}</span>
          </p>
        </div>
      </div>
      <div class="header-right">
        <button class="btn btn-secondary" @click="printReport">
          🖨️ 打印 / 导出 PDF
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="!report" class="empty-state">报告不存在</div>
    <div v-else class="report-content">
      <!-- 关键指标 -->
      <div class="metrics-section">
        <div class="metrics-grid">
          <div class="metric-card">
            <div class="metric-label">总收益率</div>
            <div class="metric-value" :class="report.summary?.total_return >= 0 ? 'positive' : 'negative'">
              {{ formatPercent(report.summary?.total_return) }}
            </div>
          </div>
          <div class="metric-card">
            <div class="metric-label">年化收益率</div>
            <div class="metric-value" :class="report.summary?.annualized_return >= 0 ? 'positive' : 'negative'">
              {{ formatPercent(report.summary?.annualized_return) }}
            </div>
          </div>
          <div class="metric-card">
            <div class="metric-label">夏普比率</div>
            <div class="metric-value">{{ report.summary?.sharpe_ratio?.toFixed(2) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">最大回撤</div>
            <div class="metric-value negative">{{ formatPercent(report.summary?.max_drawdown) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">胜率</div>
            <div class="metric-value">{{ formatPercent(report.summary?.win_rate) }}</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">交易次数</div>
            <div class="metric-value">{{ report.summary?.total_trades }}</div>
          </div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-section">
        <div class="chart-card">
          <h3>账户净值曲线</h3>
          <div ref="equityChartRef" class="chart-container"></div>
        </div>

        <div class="chart-row">
          <div class="chart-card half">
            <h3>行业分布</h3>
            <div ref="pieChartRef" class="chart-container"></div>
          </div>
          <div class="chart-card half">
            <h3>收益热力图</h3>
            <div ref="heatmapRef" class="chart-container"></div>
          </div>
        </div>
      </div>

      <!-- HTML 报告内容 -->
      <div v-if="report.html_content" class="html-content">
        <h3>详细分析</h3>
        <div class="html-wrapper" v-html="report.html_content"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts/core'
import { LineChart, PieChart, HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useAnalytics } from '@/composables/useAnalytics'
import { reportApi } from '@/api'

echarts.use([
  LineChart,
  PieChart,
  HeatmapChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  CanvasRenderer,
])

const route = useRoute()
const router = useRouter()
const { pageView } = useAnalytics()

// 状态
const report = ref<any>(null)
const loading = ref(false)

// 图表 refs
const equityChartRef = ref<HTMLElement | null>(null)
const pieChartRef = ref<HTMLElement | null>(null)
const heatmapRef = ref<HTMLElement | null>(null)

let equityChartInstance: echarts.ECharts | null = null
let pieChartInstance: echarts.ECharts | null = null
let heatmapInstance: echarts.ECharts | null = null

const reportId = computed(() => route.params.id as string)

const typeLabels: Record<string, string> = {
  daily: '日报',
  weekly: '周报',
  monthly: '月报',
}

async function loadReport() {
  loading.value = true
  try {
    const res = await reportApi.getDetail(reportId.value)
    report.value = res.data
  } catch (error) {
    console.error('Failed to load report:', error)
  } finally {
    loading.value = false
  }
}

function initEquityChart() {
  if (!equityChartRef.value || !report.value?.equity_curve) return

  equityChartInstance = echarts.getInstanceByDom(equityChartRef.value) || echarts.init(equityChartRef.value, 'dark')

  const dates = report.value.equity_curve.dates || []
  const equity = report.value.equity_curve.equity || []
  const benchmark = report.value.equity_curve.benchmark || []

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26, 26, 26, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#fff' },
    },
    grid: {
      left: 48,
      right: 24,
      top: 24,
      bottom: 32,
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.2)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
    },
    series: [
      {
        name: '账户净值',
        type: 'line',
        data: equity,
        smooth: true,
        lineStyle: { width: 2, color: '#2962FF' },
        itemStyle: { color: '#2962FF' },
      },
      {
        name: '基准',
        type: 'line',
        data: benchmark,
        smooth: true,
        lineStyle: { width: 1.6, color: 'rgba(255, 255, 255, 0.5)' },
        itemStyle: { color: 'rgba(255, 255, 255, 0.5)' },
      },
    ],
  }

  equityChartInstance.setOption(option)
}

function initPieChart() {
  if (!pieChartRef.value || !report.value?.industry_distribution) return

  pieChartInstance = echarts.getInstanceByDom(pieChartRef.value) || echarts.init(pieChartRef.value, 'dark')

  const data = Object.entries(report.value.industry_distribution || {}).map(([name, value]) => ({
    name,
    value: Number(value),
  }))

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(26, 26, 26, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#fff' },
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { color: 'rgba(255, 255, 255, 0.7)', fontSize: 10 },
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        data,
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
        label: {
          color: 'rgba(255, 255, 255, 0.7)',
          fontSize: 10,
        },
      },
    ],
  }

  pieChartInstance.setOption(option)
}

function initHeatmap() {
  if (!heatmapRef.value || !report.value?.return_heatmap) return

  heatmapInstance = echarts.getInstanceByDom(heatmapRef.value) || echarts.init(heatmapRef.value, 'dark')

  const heatmapData = report.value.return_heatmap || []
  const symbols = [...new Set(heatmapData.map((d: any) => d.symbol))]
  const dates = [...new Set(heatmapData.map((d: any) => d.date))]

  const data = heatmapData.map((d: any) => [
    dates.indexOf(d.date),
    symbols.indexOf(d.symbol),
    d.return,
  ])

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      position: 'top',
      backgroundColor: 'rgba(26, 26, 26, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#fff' },
      formatter: (params: any) => {
        return `${params.value[1]} · ${params.value[0]}<br/>收益：${(params.value[2] * 100).toFixed(2)}%`
      },
    },
    grid: {
      left: 100,
      right: 20,
      top: 40,
      bottom: 60,
    },
    xAxis: {
      type: 'category',
      data: dates,
      splitArea: { show: true },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10, rotate: 45 },
    },
    yAxis: {
      type: 'category',
      data: symbols,
      splitArea: { show: true },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
    },
    visualMap: {
      min: -0.1,
      max: 0.1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: {
        color: ['#FF1744', '#FFD600', '#00C853'],
      },
      textStyle: { color: 'rgba(255, 255, 255, 0.7)', fontSize: 10 },
    },
    series: [
      {
        name: '收益热力图',
        type: 'heatmap',
        data,
        label: { show: false },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  }

  heatmapInstance.setOption(option)
}

function goBack() {
  router.back()
}

function printReport() {
  window.print()
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return '-'
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
}

onMounted(() => {
  pageView(`/reports/${reportId.value}`)
  loadReport()
})

// 延迟初始化图表（等待 DOM 渲染）
const initCharts = () => {
  setTimeout(() => {
    initEquityChart()
    initPieChart()
    initHeatmap()
  }, 100)
}

watch(
  () => report.value,
  () => {
    initCharts()
  }
)

onBeforeUnmount(() => {
  equityChartInstance?.dispose()
  pieChartInstance?.dispose()
  heatmapInstance?.dispose()
})
</script>

<style scoped lang="scss">
.report-detail-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;

  h1 {
    margin: 4px 0 0;
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

// 指标卡片
.metrics-section {
  margin-bottom: 32px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
}

.metric-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 20px;
  text-align: center;

  .metric-label {
    font-size: 12px;
    color: var(--color-text-secondary);
    margin-bottom: 8px;
  }

  .metric-value {
    font-size: 24px;
    font-weight: 600;
    color: var(--color-text);

    &.positive { color: #00C853; }
    &.negative { color: #FF1744; }
  }
}

// 图表区域
.charts-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-bottom: 32px;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.chart-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;

  &.half {
    min-height: 320px;
  }

  h3 {
    margin: 0 0 16px;
    font-size: 16px;
    color: var(--color-text);
  }

  .chart-container {
    height: 300px;
    width: 100%;
  }
}

// HTML 内容
.html-content {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 24px;

  h3 {
    margin: 0 0 16px;
    font-size: 16px;
    color: var(--color-text);
  }

  .html-wrapper {
    color: var(--color-text);
    line-height: 1.6;

    :deep(h1), :deep(h2), :deep(h3) {
      margin-top: 1.5em;
      margin-bottom: 0.5em;
    }

    :deep(table) {
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;

      th, td {
        padding: 10px;
        border: 1px solid var(--color-border);
        text-align: left;
      }

      th {
        background: var(--color-bg-primary);
      }
    }

    :deep(.positive) { color: #00C853; }
    :deep(.negative) { color: #FF1744; }
  }
}

// 通用
.loading-state,
.empty-state {
  text-align: center;
  padding: 60px;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border-radius: 12px;
}
</style>
