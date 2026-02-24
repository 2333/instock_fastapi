<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <div class="header-left">
        <h1>数据看板</h1>
        <p class="subtitle">实时监控与分析</p>
      </div>
      <div class="header-right">
        <span class="last-updated">更新时间: {{ lastUpdated }}</span>
        <button class="btn btn-primary" @click="refreshData" :disabled="loading">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
          </svg>
          刷新
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else class="dashboard-grid">
      <!-- 今日形态 -->
      <div class="card">
        <div class="card-header">
          <h3>今日形态</h3>
          <router-link to="/patterns" class="card-link">查看全部</router-link>
        </div>
        <div class="pattern-list">
          <div v-if="recentPatterns.length === 0" class="empty-state">
            暂无形态数据
          </div>
          <div 
            v-else
            v-for="pattern in recentPatterns" 
            :key="`${pattern.code}-${pattern.type}`"
            class="pattern-item"
            @click="$router.push(`/stocks/${pattern.code}`)"
          >
            <div class="pattern-info">
              <span class="pattern-code">{{ pattern.code }}</span>
              <span class="pattern-name">{{ pattern.name }}</span>
            </div>
            <div class="pattern-meta">
              <span class="badge" :class="getSignalClass(pattern.signal)">{{ pattern.signal }}</span>
              <span class="pattern-confidence">{{ pattern.confidence }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 精选回顾 -->
      <div class="card">
        <div class="card-header">
          <h3>精选回顾</h3>
          <router-link to="/selection" class="card-link">查看全部</router-link>
        </div>
        <div class="selection-summary">
          <div class="selection-stat">
            <span class="selection-value">{{ selectionStats.total }}</span>
            <span class="selection-label">精选总数</span>
          </div>
          <div class="selection-stat">
            <span class="selection-value price-up">{{ selectionStats.winning }}</span>
            <span class="selection-label">盈利交易</span>
          </div>
          <div class="selection-stat">
            <span class="selection-value">{{ selectionStats.winRate }}%</span>
            <span class="selection-label">胜率</span>
          </div>
          <div class="selection-stat">
            <span class="selection-value">{{ formatReturn(selectionStats.avgReturn) }}%</span>
            <span class="selection-label">平均收益</span>
          </div>
        </div>
      </div>

      <!-- 快速跳转 -->
      <div class="card full-width">
        <div class="card-header">
          <h3>快速导航</h3>
        </div>
        <div class="quick-nav">
          <router-link to="/stocks" class="nav-item">
            <span class="nav-icon">📊</span>
            <span class="nav-label">股票列表</span>
          </router-link>
          <router-link to="/patterns" class="nav-item">
            <span class="nav-icon">🔄</span>
            <span class="nav-label">形态分析</span>
          </router-link>
          <router-link to="/selection" class="nav-item">
            <span class="nav-icon">✨</span>
            <span class="nav-label">精选策略</span>
          </router-link>
          <router-link to="/backtest" class="nav-item">
            <span class="nav-icon">📈</span>
            <span class="nav-label">回测分析</span>
          </router-link>
          <router-link to="/attention" class="nav-item">
            <span class="nav-icon">⭐</span>
            <span class="nav-label">我的关注</span>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { patternApi, selectionApi } from '@/api'

const lastUpdated = ref(new Date().toLocaleString())
const loading = ref(false)

interface PatternItem {
  code: string
  name: string
  type: string
  signal: string
  confidence: number
}

const recentPatterns = ref<PatternItem[]>([])

const selectionStats = reactive({
  total: 0,
  winning: 0,
  winRate: 0,
  avgReturn: 0,
})

const getLatestTradeDate = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

const getSignalClass = (signal: string) => {
  if (!signal) return 'neutral'
  const s = signal.toLowerCase()
  if (s.includes('bull') || s.includes('买') || s.includes('多')) return 'bullish'
  if (s.includes('bear') || s.includes('卖') || s.includes('空')) return 'bearish'
  return 'neutral'
}

const formatReturn = (value: number) => {
  if (!value || isNaN(value)) return '0.00'
  return value.toFixed(2)
}

const fetchPatterns = async () => {
  try {
    const date = getLatestTradeDate()
    const patterns = await patternApi.getTodayPatterns({ limit: 10 })
    if (patterns && patterns.length > 0) {
      recentPatterns.value = patterns.map((p: any) => ({
        code: p.ts_code || p.code,
        name: p.name || p.ts_code,
        type: p.pattern_name || '',
        signal: p.pattern_type || p.signal || 'neutral',
        confidence: parseFloat(p.confidence) || 0,
      }))
    }
  } catch (e) {
    console.error('获取形态数据失败:', e)
    recentPatterns.value = []
  }
}

const fetchSelectionStats = async () => {
  try {
    const history = await selectionApi.getHistory({ limit: 100 })
    if (history && history.length > 0) {
      selectionStats.total = history.length
      const winning = history.filter((r: any) => r.signal === 'buy' || r.score > 0).length
      selectionStats.winning = winning
      selectionStats.winRate = Math.round((winning / history.length) * 100 * 10) / 10
      
      const totalReturn = history.reduce((sum: number, r: any) => sum + (parseFloat(r.score) || 0), 0)
      selectionStats.avgReturn = totalReturn / history.length
    }
  } catch (e) {
    console.error('获取精选数据失败:', e)
  }
}

const refreshData = async () => {
  loading.value = true
  lastUpdated.value = new Date().toLocaleString()
  await Promise.all([
    fetchPatterns(),
    fetchSelectionStats(),
  ])
  loading.value = false
}

onMounted(() => {
  refreshData()
})
</script>

<style scoped lang="scss">
.dashboard {
  padding: 24px;
}

.dashboard-header {
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
  align-items: center;
  gap: 16px;
}

.last-updated {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
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

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.btn-primary {
    background: #2962FF;
    color: white;

    &:hover:not(:disabled) {
      background: #1E53E5;
    }
  }
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: rgba(26, 26, 26, 0.5);
  border-radius: 12px;

  p {
    margin: 16px 0;
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

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.card {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.card.full-width {
  grid-column: span 2;
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
    color: rgba(255, 255, 255, 0.9);
  }
}

.card-link {
  font-size: 13px;
  color: #2962FF;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.pattern-list {
  max-height: 300px;
  overflow-y: auto;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
}

.pattern-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  &:last-child {
    border-bottom: none;
  }
}

.pattern-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pattern-code {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.pattern-name {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.pattern-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;

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

.pattern-confidence {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.selection-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  padding: 20px;
  gap: 20px;
}

.selection-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.selection-value {
  font-size: 28px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(255, 255, 255, 0.9);
}

.selection-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.quick-nav {
  display: flex;
  gap: 16px;
  padding: 20px;
  overflow-x: auto;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  text-decoration: none;
  transition: all 0.2s;
  min-width: 100px;

  &:hover {
    background: rgba(41, 98, 255, 0.1);
    transform: translateY(-2px);
  }
}

.nav-icon {
  font-size: 24px;
}

.nav-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .card.full-width {
    grid-column: span 1;
  }

  .selection-summary {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: 16px;
  }

  .dashboard-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .selection-summary {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .quick-nav {
    flex-wrap: wrap;
  }

  .nav-item {
    min-width: calc(50% - 8px);
  }
}
</style>
