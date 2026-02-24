<template>
  <div class="backtest-page">
    <div class="page-header">
      <div class="header-left">
        <h1>策略回测</h1>
        <p class="subtitle">测试和优化您的交易策略</p>
      </div>
      <div class="header-right">
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
      <aside class="config-panel">
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
              <option value="ma_crossover">MA 交叉</option>
              <option value="rsi_oversold">RSI 超卖</option>
              <option value="macd_cross">MACD 交叉</option>
              <option value="boll_breakout">布林带突破</option>
              <option value="pattern_based">形态策略</option>
            </select>
          </div>
          <div v-if="config.strategyType === 'ma_crossover'" class="strategy-params">
            <div class="config-row">
              <div class="config-item">
                <label>快速 MA</label>
                <input type="number" v-model.number="config.fastMA" class="input-number">
              </div>
              <div class="config-item">
                <label>慢速 MA</label>
                <input type="number" v-model.number="config.slowMA" class="input-number">
              </div>
            </div>
          </div>
          <div v-if="config.strategyType === 'rsi_oversold'" class="strategy-params">
            <div class="config-row">
              <div class="config-item">
                <label>RSI 周期</label>
                <input type="number" v-model.number="config.rsiPeriod" class="input-number">
              </div>
              <div class="config-item">
                <label>超卖水平</label>
                <input type="number" v-model.number="config.oversoldLevel" class="input-number">
              </div>
            </div>
          </div>
        </div>
      </aside>

      <main class="results-panel">
        <div v-if="!hasResults" class="empty-state">
          <div class="empty-icon">📊</div>
          <h3>暂无回测结果</h3>
          <p>配置策略参数后点击"运行回测"查看结果</p>
        </div>

        <template v-else>
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
import { ref, reactive, onMounted, shallowRef } from 'vue'
import { useResizeObserver } from '@vueuse/core'

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

const loading = ref(false)
const hasResults = ref(false)
const equityChartRef = ref<HTMLDivElement>()
const equityChartInstance = shallowRef<any>(null)

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
  fastMA: 5,
  slowMA: 20,
  rsiPeriod: 14,
  oversoldLevel: 30,
})

const metrics = reactive({
  initialCapital: 100000,
  finalCapital: 128500,
  totalReturn: 28.5,
  annualizedReturn: 12.3,
  maxDrawdown: -8.5,
  sharpeRatio: 1.45,
  winRate: 62.5,
  totalTrades: 48,
  winningTrades: 30,
  profitFactor: 1.85,
  avgWin: 3200,
  avgLoss: -1800,
})

const trades = ref<Trade[]>([
  { id: 1, date: '2024-02-10', type: 'BUY', price: 1620.50, quantity: 61, profit: 0, returnPct: 0, holdDays: 0 },
  { id: 2, date: '2024-02-15', type: 'SELL', price: 1650.00, quantity: 61, profit: 1800, returnPct: 1.82, holdDays: 5 },
  { id: 3, date: '2024-02-22', type: 'BUY', price: 1635.20, quantity: 61, profit: 0, returnPct: 0, holdDays: 0 },
  { id: 4, date: '2024-03-05', type: 'SELL', price: 1590.00, quantity: 61, profit: -2760, returnPct: -2.76, holdDays: 12 },
  { id: 5, date: '2024-03-12', type: 'BUY', price: 1575.80, quantity: 62, profit: 0, returnPct: 0, holdDays: 0 },
  { id: 6, date: '2024-03-25', type: 'SELL', price: 1680.00, quantity: 62, profit: 6450, returnPct: 6.61, holdDays: 13 },
])

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

const loadTemplate = () => {
  console.log('Loading template...')
}

const runBacktest = async () => {
  loading.value = true
  await new Promise(resolve => setTimeout(resolve, 3000))
  hasResults.value = true
  loading.value = false
  initEquityChart()
}

const initEquityChart = async () => {
  if (!equityChartRef.value) return

  const echarts = (await import('echarts')).default
  equityChartInstance.value = echarts.init(equityChartRef.value, 'dark', {
    renderer: 'canvas',
  })

  const dates = Array.from({ length: 252 }, (_, i) => {
    const date = new Date()
    date.setDate(date.getDate() - (251 - i))
    return date.toISOString().split('T')[0]
  })

  const equityData = [100000]
  for (let i = 1; i < 252; i++) {
    const change = (Math.random() - 0.48) * 2
    equityData.push(equityData[i - 1] * (1 + change / 100))
  }

  const benchmarkData = [100000]
  for (let i = 1; i < 252; i++) {
    const change = (Math.random() - 0.49) * 1.5
    benchmarkData.push(benchmarkData[i - 1] * (1 + change / 100))
  }

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
          html += `<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <span style="width: 10px; height: 10px; border-radius: 2px; background: ${p.color};"></span>
            <span>${p.seriesName}: ${formatCurrency(p.value)}</span>
          </div>`
        })
        return html
      },
    },
    legend: { show: false },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.5)', fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      scale: true,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: {
        color: 'rgba(255, 255, 255, 0.5)',
        fontSize: 10,
        formatter: (value: number) => (value / 10000).toFixed(0) + '万',
      },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
    },
    series: [
      {
        name: 'Portfolio',
        type: 'line',
        data: equityData,
        smooth: true,
        lineStyle: { width: 2, color: '#2962FF' },
        itemStyle: { color: '#2962FF' },
      },
      {
        name: 'Benchmark',
        type: 'line',
        data: benchmarkData,
        smooth: true,
        lineStyle: { width: 1.5, color: 'rgba(255, 255, 255, 0.4)' },
        itemStyle: { color: 'rgba(255, 255, 255, 0.4)' },
      },
    ],
  }

  equityChartInstance.value.setOption(option)

  useResizeObserver(equityChartRef, () => {
    equityChartInstance.value?.resize()
  })
}

onMounted(() => {
  if (hasResults.value) {
    initEquityChart()
  }
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
  gap: 24px;
}

.config-panel {
  width: 320px;
  flex-shrink: 0;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  max-height: calc(100vh - 180px);
  overflow-y: auto;
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

.strategy-params {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
}

.results-panel {
  flex: 1;
  min-width: 0;
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
