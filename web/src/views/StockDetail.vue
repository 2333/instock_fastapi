<template>
  <div class="stock-detail-page">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
    
    <template v-else-if="stockInfo">
      <div class="page-header">
        <div class="stock-info">
          <h1>{{ stockInfo.name }}</h1>
          <div class="stock-meta">
            <span class="stock-code">{{ stockInfo.code }}</span>
            <span class="stock-market">{{ marketLabel }}</span>
          </div>
        </div>
        <div class="price-info">
          <div class="current-price" :class="change >= 0 ? 'price-up' : 'price-down'">
            {{ latestBar?.close?.toFixed(2) || '-' }}
          </div>
          <div class="price-change" :class="change >= 0 ? 'price-up' : 'price-down'">
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
                业务图表
              </button>
              <button
                class="chart-mode-btn"
                :class="{ active: activeChartMode === 'tradingview' }"
                @click="activeChartMode = 'tradingview'"
              >
                TradingView
              </button>
            </div>
            <p class="chart-mode-copy">
              {{
                activeChartMode === 'native'
                  ? '使用站内行情、复权与现有指标逻辑。'
                  : '使用 TradingView 内置行情与指标，作为补充分析视图。'
              }}
            </p>
          </div>

          <KLineChart
            v-if="activeChartMode === 'native'"
            :title="stockInfo.name"
            :data="klineData"
            :loading="loading"
            :adjust="currentAdjust"
            :external-hint="chartHint"
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
            <h3>股票概况</h3>
            <div class="profile-grid">
              <div class="profile-item">
                <span class="label">开盘价</span>
                <span class="value">{{ latestBar?.open?.toFixed(2) || '-' }}</span>
              </div>
              <div class="profile-item">
                <span class="label">最高价</span>
                <span class="value">{{ latestBar?.high?.toFixed(2) || '-' }}</span>
              </div>
              <div class="profile-item">
                <span class="label">最低价</span>
                <span class="value">{{ latestBar?.low?.toFixed(2) || '-' }}</span>
              </div>
              <div class="profile-item">
                <span class="label">成交量</span>
                <span class="value">{{ formatVolume(latestBar?.vol) }}</span>
              </div>
              <div class="profile-item">
                <span class="label">成交额</span>
                <span class="value">{{ formatTurnover(latestBar?.amount) }}</span>
              </div>
              <div class="profile-item">
                <span class="label">所属行业</span>
                <span class="value">{{ stockInfo.industry || '-' }}</span>
              </div>
              <div class="profile-item">
                <span class="label">上市日期</span>
                <span class="value">{{ stockInfo.list_date || '-' }}</span>
              </div>
            </div>
          </div>

          <div class="panel-section">
            <h3>快速操作</h3>
            <div class="action-buttons">
              <button class="action-btn primary" @click="goBacktest">
                <span class="btn-icon">⚡</span>
                <span>回测策略</span>
              </button>
              <button class="action-btn" @click="addToWatchlist">
                <span class="btn-icon">⭐</span>
                <span>{{ inWatchlist ? '取消关注' : '添加到关注' }}</span>
              </button>
              <button class="action-btn" @click="analyzePatterns">
                <span class="btn-icon">🔍</span>
                <span>分析形态</span>
              </button>
            </div>
          </div>

          <div class="panel-section">
            <h3>相关形态</h3>
            <p v-if="activeChartMode === 'tradingview'" class="pattern-note">
              列表仍来自站内形态识别；TradingView 视图不会直接显示这些业务标记。
            </p>
            <div v-if="patterns.length > 0" class="pattern-list">
              <div 
                v-for="pattern in patterns" 
                :key="pattern.pattern_name"
                class="pattern-item"
              >
                <div class="pattern-info">
                  <span class="pattern-name">{{ getPatternLabel(pattern.pattern_name) }}</span>
                  <span class="pattern-date">{{ pattern.trade_date }}</span>
                </div>
                <div class="pattern-badge" :class="pattern.pattern_type">
                  {{ pattern.confidence }}%
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              暂无形态数据
            </div>
          </div>
        </aside>
      </div>
    </template>
    
    <div v-else class="error-state">
      <p>未找到股票信息</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { stockApi, patternApi, attentionApi } from '@/api'
import KLineChart from '@/components/charts/KLineChart.vue'
import TradingViewWidget from '@/components/charts/TradingViewWidget.vue'

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
  trade_date?: string
}

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const inWatchlist = ref(false)
const activeChartMode = ref<'native' | 'tradingview'>('native')

const stockInfo = ref<any>(null)
const klineData = ref<KlineData[]>([])
const patterns = ref<any[]>([])
const currentAdjust = ref<'bfq' | 'qfq' | 'hfq'>('qfq')
const chartHint = ref('')
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')

const code = computed(() => route.params.code as string)
const marketLabel = computed(() => {
  const exchange = String(stockInfo.value?.exchange || '').toUpperCase()
  if (exchange === 'SSE' || exchange === 'SH') return '上海'
  if (exchange === 'SZSE' || exchange === 'SZ') return '深圳'
  if (exchange === 'BSE' || exchange === 'BJ') return '北交所'
  return exchange || '-'
})

const latestBar = computed<BarData | null>(() => {
  if (klineData.value.length > 0) {
    const last = klineData.value[klineData.value.length - 1]
    return {
      open: last.open,
      high: last.high,
      low: last.low,
      close: last.close,
      vol: last.volume,
      amount: last.amount,
    }
  }
  return null
})

const change = computed(() => {
  if (!latestBar.value) return 0
  return Number(latestBar.value.close) - Number(latestBar.value.open)
})

const changeValue = computed(() => {
  if (!latestBar.value) return 0
  return ((Number(latestBar.value.close) - Number(latestBar.value.open)) / Number(latestBar.value.open)) * 100
})

const formatVolume = (volume: number | undefined) => {
  if (!volume) return '-'
  if (volume >= 1000000) return (volume / 1000000).toFixed(2) + 'M'
  if (volume >= 1000) return (volume / 1000).toFixed(2) + 'K'
  return volume.toString()
}

const formatTurnover = (turnover: number | undefined) => {
  if (!turnover) return '-'
  if (turnover >= 1000000000) return (turnover / 1000000000).toFixed(2) + 'B'
  if (turnover >= 1000000) return (turnover / 1000000).toFixed(2) + 'M'
  return (turnover / 1000).toFixed(2) + 'K'
}

const formatChange = (val: number) => {
  const prefix = val >= 0 ? '+' : ''
  return `${prefix}${val.toFixed(2)}%`
}

const getPatternLabel = (name: string) => {
  const labels: Record<string, string> = {
    'MORNING_STAR': '晨星',
    'EVENING_STAR': '夜星',
    'BREAKTHROUGH_HIGH': '突破高点',
    'BREAKDOWN_LOW': '跌破低点',
    'CONTINUOUS_RISE': '连续上涨',
    'CONTINUOUS_FALL': '连续下跌',
  }
  return labels[name] || name
}

const fetchStockDetail = async (
  adjust: 'bfq' | 'qfq' | 'hfq' = currentAdjust.value,
  refreshPatterns = false
) => {
  loading.value = true
  try {
    const endDate = getLatestTradeDate()
    const startDate = getStartDate(180)
    
    const stockPromise = stockApi.getStockDetail(code.value, { start_date: startDate, end_date: endDate, adjust })
    const patternPromise = refreshPatterns
      ? patternApi.getPatterns(code.value, { limit: 10 }).catch((e: any) => {
          console.error('获取形态数据失败:', e)
          return []
        })
      : Promise.resolve(patterns.value)
    const [stockData, patternsData] = await Promise.all([stockPromise, patternPromise])
    
    stockInfo.value = stockData
    chartHint.value =
      stockData?.adjust_note === 'requested_adjust_data_unavailable_fallback_to_bfq'
        ? '当前复权数据暂不可用，已自动回退为不复权数据'
        : ''
    
    patterns.value = (patternsData || []).map((p: any) => ({
      ...p,
      trade_date: p.trade_date || '',
      confidence: p.confidence ? Math.round(p.confidence) : 0,
    }))
    
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
    }
    await syncWatchlistStatus()
  } catch (e) {
    console.error('Failed to fetch stock detail:', e)
  } finally {
    loading.value = false
  }
}

const getLatestTradeDate = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

const getStartDate = (daysBack: number) => {
  const date = new Date()
  date.setDate(date.getDate() - daysBack)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
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
  } catch (e) {
    console.error('Failed to update watchlist:', e)
    showNotification?.('error', '更新关注状态失败')
  }
}

const analyzePatterns = () => {
  router.push({ path: '/patterns', query: { code: code.value } })
}

const goBacktest = () => {
  router.push({ path: '/backtest', query: { code: code.value } })
}

const syncWatchlistStatus = async () => {
  try {
    const list = await attentionApi.getList()
    const target = code.value
    inWatchlist.value = (list || []).some((item: any) => {
      const raw = item.code || item.symbol || item.ts_code?.split('.')?.[0]
      return raw === target
    })
  } catch {
    inWatchlist.value = false
  }
}

// 监听路由参数变化，切换股票时重新加载
watch(code, () => {
  fetchStockDetail(currentAdjust.value, true)
})

onMounted(() => {
  fetchStockDetail(currentAdjust.value, true)
})
</script>

<style scoped lang="scss">
.stock-detail-page {
  padding: 24px;
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
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
  to { transform: rotate(360deg); }
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.stock-info {
  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
  }
}

.stock-meta {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  
  .stock-code {
    font-family: 'JetBrains Mono', monospace;
    color: rgba(255, 255, 255, 0.7);
  }
  
  .stock-market {
    color: rgba(255, 255, 255, 0.5);
  }
}

.price-info {
  text-align: right;
  
  .current-price {
    font-size: 36px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
  }
  
  .price-change {
    font-size: 16px;
    margin-top: 4px;
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
  opacity: 0.7;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
  flex: 1;
  min-height: 0;
}

.main-chart {
  background: rgba(26, 26, 26, 0.5);
  border-radius: 12px;
  overflow: hidden;
  min-width: 0;
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

.side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.panel-section {
  background: rgba(26, 26, 26, 0.5);
  border-radius: 12px;
  padding: 20px;
  
  h3 {
    margin: 0 0 16px;
    font-size: 16px;
    font-weight: 600;
  }
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
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
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(255, 255, 255, 0.05);
  }
  
  &.primary {
    background: rgba(41, 98, 255, 0.15);
    border-color: #2962FF;
    color: #2962FF;
  }
}

.pattern-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pattern-note {
  margin: 0 0 12px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.pattern-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}

.pattern-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  
  .pattern-name {
    font-size: 13px;
    font-weight: 500;
  }
  
  .pattern-date {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.4);
  }
}

.pattern-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(0, 200, 83, 0.15);
  color: #00C853;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: rgba(255, 255, 255, 0.4);
}

@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
  
  .side-panel {
    flex-direction: row;
    flex-wrap: wrap;
  }
  
  .panel-section {
    flex: 1;
    min-width: 280px;
  }
}

@media (max-width: 768px) {
  .stock-detail-page {
    padding: 16px;
    height: auto;
    min-height: calc(100vh - 60px);
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .price-info {
    text-align: left;
  }

  .chart-mode-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .chart-mode-copy {
    text-align: left;
  }
  
  .current-price {
    font-size: 28px;
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
  
  .action-buttons {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .page-header h1 {
    font-size: 22px;
  }
  
  .stock-meta {
    flex-direction: column;
    gap: 4px;
  }
  
  .current-price {
    font-size: 24px;
  }
  
  .price-change {
    font-size: 14px;
  }
}
</style>
