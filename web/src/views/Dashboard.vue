<template>
  <div class="dashboard-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Phase 0 工作台</p>
        <h1>重新进入扫描与验证</h1>
        <p class="subtitle">
          首页只保留四个真实入口，帮助你从最近一次扫描、关注和验证继续往下走。
        </p>
      </div>
      <div class="header-actions">
        <div class="sync-meta">
          <span class="sync-label">最近刷新</span>
          <strong>{{ lastSyncedLabel }}</strong>
        </div>
        <button class="refresh-btn" @click="refreshWorkbench" :disabled="loading">
          {{ loading ? '刷新中...' : '刷新工作台' }}
        </button>
      </div>
    </header>

    <div v-if="loadWarnings.length" class="warning-banner">
      <strong>部分卡片未完成加载</strong>
      <span>{{ loadWarnings.join(' / ') }}</span>
    </div>

    <section class="health-strip">
      <div class="card-header health-strip__header">
        <div>
          <span class="card-kicker">数据任务健康</span>
          <h2>关键更新状态</h2>
        </div>
        <span :class="healthToneClass">{{ healthToneLabel }}</span>
      </div>

      <div class="metric-strip metric-strip--compact metric-strip--health">
        <div class="metric-block">
          <span class="metric-value">{{ staleDatasetCount }}</span>
          <span class="metric-label">滞后数据集</span>
        </div>
        <div class="metric-block">
          <span class="metric-value" :class="{ 'metric-value--negative': activeAlertCount > 0 }">
            {{ activeAlertCount }}
          </span>
          <span class="metric-label">活动告警</span>
        </div>
        <div class="metric-block">
          <span class="metric-value metric-value--small">{{ baselineTradeDateLabel }}</span>
          <span class="metric-label">基准交易日</span>
        </div>
        <div class="metric-block">
          <span class="metric-value metric-value--small">{{ topAlertDatasetLabel }}</span>
          <span class="metric-label">最高优先提示</span>
        </div>
      </div>

      <p class="card-description health-strip__description">
        <template v-if="topAlertSummary">
          {{ topAlertSummary }}
        </template>
        <template v-else-if="staleDatasetNames.length">
          当前滞后数据集：{{ staleDatasetNames.join(' / ') }}。
        </template>
        <template v-else>
          关键市场数据已对齐到基准交易日，首页暂未发现需要优先处理的更新异常。
        </template>
      </p>

      <div v-if="staleDatasetNames.length || alertBadgeLabels.length" class="health-strip__tags">
        <span v-for="label in staleDatasetNames" :key="`stale-${label}`" class="health-tag health-tag--stale">
          滞后：{{ label }}
        </span>
        <span v-for="label in alertBadgeLabels" :key="`alert-${label}`" class="health-tag health-tag--alert">
          告警：{{ label }}
        </span>
      </div>
    </section>

    <div class="card-grid">
      <section class="workbench-card">
        <div class="card-header">
          <div>
            <span class="card-kicker">扫描温度</span>
            <h2>今日形态摘要</h2>
          </div>
          <router-link to="/patterns" class="card-link">进入形态识别</router-link>
        </div>

        <div class="metric-strip">
          <div class="metric-block">
            <span class="metric-value">{{ patternSummary.total }}</span>
            <span class="metric-label">命中总数</span>
          </div>
          <div class="metric-block">
            <span class="metric-value metric-value--positive">{{ patternSummary.bullish }}</span>
            <span class="metric-label">看涨</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ patternSummary.neutral }}</span>
            <span class="metric-label">中性</span>
          </div>
          <div class="metric-block">
            <span class="metric-value metric-value--negative">{{ patternSummary.bearish }}</span>
            <span class="metric-label">看跌</span>
          </div>
        </div>

        <p class="card-description">
          <template v-if="patternSummary.tradeDate">
            最近评估交易日 {{ formatDisplayDate(patternSummary.tradeDate) }}，优先从置信度更高的形态回到个股详情。
          </template>
          <template v-else>
            当前没有可展示的形态结果，进入形态识别页可重新扫描。
          </template>
        </p>

        <div v-if="topPatterns.length" class="list-stack">
          <router-link
            v-for="pattern in topPatterns"
            :key="`${pattern.code}-${pattern.patternName}-${pattern.tradeDate}`"
            :to="buildStockLink(pattern.code, pattern.tradeDate)"
            class="list-row"
          >
            <div>
              <strong>{{ pattern.code }}</strong>
              <span>{{ pattern.name }}</span>
            </div>
            <div class="row-meta">
              <span :class="signalBadgeClass(pattern.signal)">{{ signalLabel(pattern.signal) }}</span>
              <span>{{ pattern.confidence.toFixed(0) }}%</span>
            </div>
          </router-link>
        </div>
      </section>

      <section class="workbench-card">
        <div class="card-header">
          <div>
            <span class="card-kicker">我的关注</span>
            <h2>关注列表回看</h2>
          </div>
          <router-link to="/attention" class="card-link">管理关注</router-link>
        </div>

        <div class="metric-strip metric-strip--compact">
          <div class="metric-block">
            <span class="metric-value">{{ attentionItems.length }}</span>
            <span class="metric-label">已关注股票</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ latestAttentionDateLabel }}</span>
            <span class="metric-label">最近加入</span>
          </div>
        </div>

        <p class="card-description">
          <template v-if="attentionItems.length">
            从关注列表直接回到个股详情，继续核对走势与筛选证据。
          </template>
          <template v-else>
            暂无关注股票，可在详情页或关注页补充观察名单。
          </template>
        </p>

        <div v-if="topAttentionItems.length" class="list-stack">
          <router-link
            v-for="stock in topAttentionItems"
            :key="stock.code"
            :to="buildStockLink(stock.code)"
            class="list-row"
          >
            <div>
              <strong>{{ stock.code }}</strong>
              <span>{{ stock.name }}</span>
            </div>
            <div class="row-meta">
              <span>{{ formatDisplayDate(stock.createdAt) }}</span>
            </div>
          </router-link>
        </div>
      </section>

      <section class="workbench-card">
        <div class="card-header">
          <div>
            <span class="card-kicker">最新筛选</span>
            <h2>最近一次筛选结果</h2>
          </div>
          <router-link to="/selection" class="card-link">继续筛选</router-link>
        </div>

        <div class="metric-strip metric-strip--compact">
          <div class="metric-block">
            <span class="metric-value">{{ latestScreeningCount }}</span>
            <span class="metric-label">最新命中</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ latestScreeningDateLabel }}</span>
            <span class="metric-label">筛选交易日</span>
          </div>
        </div>

        <p class="card-description">
          <template v-if="latestScreeningCount > 0">
            保留最近交易日的筛选命中，便于直接重回结果页或逐只进入验证详情。
          </template>
          <template v-else>
            还没有筛选历史，进入股票精选页可发起新的规范筛选。
          </template>
        </p>

        <div v-if="latestScreeningItems.length" class="list-stack">
          <router-link
            v-for="item in latestScreeningItems"
            :key="`${item.code}-${item.tradeDate}`"
            :to="buildStockLink(item.code, item.tradeDate)"
            class="list-row"
          >
            <div>
              <strong>{{ item.code }}</strong>
              <span>{{ item.name }}</span>
            </div>
            <div class="row-meta">
              <span>{{ item.score.toFixed(1) }} 分</span>
            </div>
          </router-link>
        </div>
      </section>

      <section class="workbench-card">
        <div class="card-header">
          <div>
            <span class="card-kicker">最近验证</span>
            <h2>历史验证入口</h2>
          </div>
          <router-link to="/selection" class="card-link">查看历史</router-link>
        </div>

        <div class="metric-strip metric-strip--compact">
          <div class="metric-block">
            <span class="metric-value">{{ latestValidationCount }}</span>
            <span class="metric-label">历史记录</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ latestValidationDateLabel }}</span>
            <span class="metric-label">最近日期</span>
          </div>
        </div>

        <p class="card-description">
          <template v-if="latestValidationCount > 0">
            从历史筛选记录回到个股详情，继续核查价格、指标和形态是否支持当时结论。
          </template>
          <template v-else>
            暂无历史验证记录，当前首页不会伪造策略或回测摘要。
          </template>
        </p>

        <div v-if="latestValidationItems.length" class="list-stack">
          <router-link
            v-for="item in latestValidationItems"
            :key="item.selectionId"
            :to="buildStockLink(item.code, item.tradeDate)"
            class="list-row"
          >
            <div>
              <strong>{{ item.code }}</strong>
              <span>{{ item.name }}</span>
            </div>
            <div class="row-meta">
              <span>{{ item.score.toFixed(1) }} 分</span>
            </div>
          </router-link>
        </div>
      </section>

      <section class="workbench-card">
        <div class="card-header">
          <div>
            <span class="card-kicker">最近查看</span>
            <h2>最近浏览的股票</h2>
          </div>
        </div>

        <div v-if="recentViewedStocks.length === 0" class="empty-hint">
          暂无最近查看的股票记录
        </div>

        <div v-else class="list-stack">
          <router-link
            v-for="item in recentViewedStocks"
            :key="item.code"
            :to="`/stock/${item.code}`"
            class="list-row"
          >
            <div>
              <strong>{{ item.code }}</strong>
              <span>{{ item.name }}</span>
            </div>
            <div class="row-meta">
              <span>{{ formatCompactDateRelative(item.viewedAt) }}</span>
            </div>
          </router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { attentionApi, marketApi, patternApi, selectionApi } from '@/api'

interface AttentionEntry {
  code: string
  name: string
  createdAt: string
}

interface ScreeningEntry {
  selectionId: string
  code: string
  name: string
  tradeDate: string
  score: number
}

interface PatternEntry {
  code: string
  name: string
  tradeDate: string
  confidence: number
  signal: string
  patternName: string
}

interface MarketTaskDatasetStatus {
  dataset: string
  latestTradeDate: string
  baselineTradeDate: string
  current: boolean
}

interface MarketTaskHealthAlert {
  taskName: string
  entityType: string
  entityKey: string
  tradeDate: string
  status: string
  source: string
  note: string
  updatedAt: string
}

const loading = ref(false)
const lastSyncedAt = ref('')
const loadWarnings = ref<string[]>([])

const attentionItems = ref<AttentionEntry[]>([])
const screeningItems = ref<ScreeningEntry[]>([])
const validationItems = ref<ScreeningEntry[]>([])
const patternItems = ref<PatternEntry[]>([])
const taskDatasets = ref<MarketTaskDatasetStatus[]>([])
const taskAlerts = ref<MarketTaskHealthAlert[]>([])
const taskHealthBaselineTradeDate = ref('')
const taskAlertCount = ref(0)
const recentViewedStocks = ref<Array<{ code: string; name: string; viewedAt: string }>>([])

const normalizeList = <T>(response: unknown, fallback: T[] = []): T[] => {
  if (Array.isArray(response)) return response as T[]
  if (response && typeof response === 'object') {
    const payload = (response as { data?: unknown }).data
    if (Array.isArray(payload)) return payload as T[]
  }
  return fallback
}

const normalizeScreeningHistory = (response: unknown) => {
  if (response && typeof response === 'object') {
    const payload = (response as { data?: { items?: unknown[] } }).data
    if (payload && Array.isArray(payload.items)) {
      return payload.items
    }
  }
  return []
}

const coerceNumber = (value: unknown) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const normalizeAttentionEntry = (item: any): AttentionEntry => ({
  code: String(item?.code || item?.symbol || item?.ts_code?.split('.')?.[0] || ''),
  name: String(item?.stock_name || item?.name || item?.code || '--'),
  createdAt: String(item?.created_at || ''),
})

const normalizeScreeningEntry = (item: any): ScreeningEntry => ({
  selectionId: String(item?.selection_id || `${item?.code || ''}-${item?.trade_date || item?.date || ''}`),
  code: String(item?.code || item?.ts_code?.split('.')?.[0] || ''),
  name: String(item?.stock_name || item?.name || item?.code || '--'),
  tradeDate: String(item?.trade_date || item?.date || ''),
  score: coerceNumber(item?.score),
})

const normalizePatternEntry = (item: any): PatternEntry => ({
  code: String(item?.code || item?.symbol || item?.ts_code?.split('.')?.[0] || ''),
  name: String(item?.stock_name || item?.name || item?.code || '--'),
  tradeDate: String(item?.trade_date || item?.date || ''),
  confidence: coerceNumber(item?.confidence),
  signal: String(item?.pattern_type || item?.signal || 'neutral'),
  patternName: String(item?.pattern_name || item?.type || ''),
})

const normalizeTaskDatasetStatus = (item: any): MarketTaskDatasetStatus => ({
  dataset: String(item?.dataset || '--'),
  latestTradeDate: String(item?.latest_trade_date || ''),
  baselineTradeDate: String(item?.baseline_trade_date || ''),
  current: Boolean(item?.current),
})

const normalizeTaskAlert = (item: any): MarketTaskHealthAlert => ({
  taskName: String(item?.task_name || '--'),
  entityType: String(item?.entity_type || ''),
  entityKey: String(item?.entity_key || ''),
  tradeDate: String(item?.trade_date || ''),
  status: String(item?.status || ''),
  source: String(item?.source || ''),
  note: String(item?.note || ''),
  updatedAt: String(item?.updated_at || ''),
})

const signalKey = (signal: string) => {
  const normalized = signal.toLowerCase()
  if (normalized.includes('bull') || normalized.includes('买') || normalized.includes('多')) return 'bullish'
  if (normalized.includes('bear') || normalized.includes('卖') || normalized.includes('空')) return 'bearish'
  return 'neutral'
}

const groupByLatestDate = (items: ScreeningEntry[]) => {
  const latestDate = items.reduce((latest, item) => {
    return item.tradeDate > latest ? item.tradeDate : latest
  }, '')
  return {
    latestDate,
    items: items.filter((item) => item.tradeDate === latestDate),
  }
}

const patternSummary = computed(() => {
  const summary = {
    total: patternItems.value.length,
    bullish: 0,
    neutral: 0,
    bearish: 0,
    tradeDate: '',
  }

  for (const item of patternItems.value) {
    summary.tradeDate = item.tradeDate > summary.tradeDate ? item.tradeDate : summary.tradeDate
    const key = signalKey(item.signal)
    if (key === 'bullish') summary.bullish += 1
    if (key === 'bearish') summary.bearish += 1
    if (key === 'neutral') summary.neutral += 1
  }

  return summary
})

const topPatterns = computed(() => {
  return [...patternItems.value]
    .sort((a, b) => b.confidence - a.confidence || b.tradeDate.localeCompare(a.tradeDate))
    .slice(0, 3)
})

const topAttentionItems = computed(() => attentionItems.value.slice(0, 3))

const latestScreeningGroup = computed(() => groupByLatestDate(screeningItems.value))
const latestValidationGroup = computed(() => groupByLatestDate(validationItems.value))

const latestScreeningItems = computed(() => {
  return [...latestScreeningGroup.value.items]
    .sort((a, b) => b.score - a.score || a.code.localeCompare(b.code))
    .slice(0, 3)
})

const latestValidationItems = computed(() => {
  return [...latestValidationGroup.value.items]
    .sort((a, b) => b.score - a.score || a.code.localeCompare(b.code))
    .slice(0, 3)
})

const latestScreeningCount = computed(() => latestScreeningGroup.value.items.length)
const latestValidationCount = computed(() => latestValidationGroup.value.items.length)
const staleDatasets = computed(() => taskDatasets.value.filter((item) => !item.current))
const staleDatasetCount = computed(() => staleDatasets.value.length)
const activeAlertCount = computed(() => {
  return taskAlertCount.value > 0 ? taskAlertCount.value : taskAlerts.value.length
})
const baselineTradeDateLabel = computed(() => {
  return taskHealthBaselineTradeDate.value ? formatDisplayDate(taskHealthBaselineTradeDate.value) : '--'
})
const staleDatasetNames = computed(() => {
  return staleDatasets.value
    .slice(0, 3)
    .map((item) => humanizeDatasetName(item.dataset))
})
const alertBadgeLabels = computed(() => {
  return taskAlerts.value
    .slice(0, 2)
    .map((item) => `${humanizeTaskName(item.taskName)} / ${humanizeTaskEntity(item.entityType, item.entityKey)}`)
})
const topAlert = computed(() => taskAlerts.value[0] || null)
const topAlertDatasetLabel = computed(() => {
  if (topAlert.value) return `${humanizeTaskName(topAlert.value.taskName)} / ${humanizeTaskEntity(topAlert.value.entityType, topAlert.value.entityKey)}`
  if (staleDatasets.value[0]) return humanizeDatasetName(staleDatasets.value[0].dataset)
  return '已对齐'
})
const healthToneLabel = computed(() => {
  if (activeAlertCount.value > 0) return '需处理'
  if (staleDatasetCount.value > 0) return '有滞后'
  return '正常'
})
const healthToneClass = computed(() => {
  if (activeAlertCount.value > 0) return 'signal-badge signal-badge--bearish'
  if (staleDatasetCount.value > 0) return 'signal-badge signal-badge--neutral'
  return 'signal-badge signal-badge--bullish'
})
const topAlertSummary = computed(() => {
  if (!topAlert.value) return ''

  const parts = [humanizeTaskName(topAlert.value.taskName), humanizeTaskEntity(topAlert.value.entityType, topAlert.value.entityKey)]
  if (topAlert.value.tradeDate) {
    parts.push(`交易日 ${formatDisplayDate(topAlert.value.tradeDate)}`)
  }
  if (topAlert.value.source) {
    parts.push(`来源 ${humanizeTaskSource(topAlert.value.source)}`)
  }
  if (topAlert.value.note) {
    parts.push(topAlert.value.note)
  } else {
    parts.push(`状态 ${humanizeTaskStatus(topAlert.value.status)}`)
  }
  return parts.join('，')
})

const lastSyncedLabel = computed(() => {
  return lastSyncedAt.value ? formatDisplayDate(lastSyncedAt.value, true) : '--'
})

const latestScreeningDateLabel = computed(() => {
  return latestScreeningGroup.value.latestDate
    ? formatDisplayDate(latestScreeningGroup.value.latestDate)
    : '--'
})

const latestValidationDateLabel = computed(() => {
  return latestValidationGroup.value.latestDate
    ? formatDisplayDate(latestValidationGroup.value.latestDate)
    : '--'
})

const latestAttentionDateLabel = computed(() => {
  const latest = attentionItems.value[0]?.createdAt
  return latest ? formatDisplayDate(latest) : '--'
})

const humanizeDatasetName = (value: string) => {
  const labels: Record<string, string> = {
    daily_bars: '日线行情',
    fund_flows: '资金流向',
    stock_tops: '龙虎榜',
    stock_top: '龙虎榜',
    stock_block_trades: '大宗交易',
    block_trades: '大宗交易',
    north_bound_funds: '北向资金',
    north_bound: '北向资金',
  }
  return labels[value] || value.replace(/_/g, ' ')
}

const humanizeTaskName = (value: string) => {
  const labels: Record<string, string> = {
    fetch_daily_data: '日线数据抓取',
    fetch_fund_flow: '资金流抓取',
    fetch_market_reference: '市场参考抓取',
    fetch_block_trades: '大宗交易抓取',
    fetch_north_bound: '北向资金抓取',
  }
  return labels[value] || value.replace(/^fetch_/, '').replace(/_/g, ' ')
}

const humanizeTaskEntity = (entityType: string, entityKey: string) => {
  const entityLabels: Record<string, string> = {
    stock_list: entityKey === 'ETF' ? 'ETF 列表' : 'A 股列表',
    stock_fund_flow: '个股资金流',
    sector_fund_flow: entityKey === 'industry' ? '行业资金流' : '板块资金流',
    stock_top: '龙虎榜',
    block_trade: '大宗交易',
  }
  return entityLabels[entityType] || entityKey || entityType || '--'
}

const humanizeTaskStatus = (value: string) => {
  const labels: Record<string, string> = {
    done: '完成',
    nodata: '无数据',
    needs_fallback: '需要降级/补救',
    failed: '失败',
  }
  return labels[value] || value || '--'
}

const humanizeTaskSource = (value: string) => {
  const labels: Record<string, string> = {
    tushare: 'Tushare',
    baostock: 'BaoStock',
    eastmoney: '东方财富',
    mixed: '混合来源',
  }
  return labels[value] || value || '--'
}

const formatDisplayDate = (value: string, withTime = false) => {
  if (!value) return '--'

  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value
  }

  if (/^\d{8}$/.test(value)) {
    return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  const options: Intl.DateTimeFormatOptions = withTime
    ? {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }
    : {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }
  return new Intl.DateTimeFormat('zh-CN', options).format(date)
}

const buildStockLink = (code: string, screeningDate?: string) => ({
  path: `/stock/${code}`,
  query: screeningDate ? { screening_date: screeningDate } : undefined,
})

const formatCompactDateRelative = (isoString: string) => {
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`
  return formatDisplayDate(isoString)
}

const signalLabel = (signal: string) => {
  const key = signalKey(signal)
  if (key === 'bullish') return '看涨'
  if (key === 'bearish') return '看跌'
  return '中性'
}

const signalBadgeClass = (signal: string) => `signal-badge signal-badge--${signalKey(signal)}`

const refreshWorkbench = async () => {
  loading.value = true
  loadWarnings.value = []

  const results = await Promise.allSettled([
    attentionApi.getList(),
    selectionApi.getScreeningHistory({ limit: 60 }),
    selectionApi.getHistory({ limit: 60 }),
    patternApi.getTodayPatterns({ limit: 120, min_confidence: 60 }),
    marketApi.getTaskHealth(5),
  ])

  const [attentionResult, screeningResult, validationResult, patternResult, taskHealthResult] = results

  if (attentionResult.status === 'fulfilled') {
    attentionItems.value = normalizeList(attentionResult.value).map(normalizeAttentionEntry)
  } else {
    attentionItems.value = []
    loadWarnings.value.push('关注列表')
    console.error('Failed to fetch attention list:', attentionResult.reason)
  }

  if (screeningResult.status === 'fulfilled') {
    screeningItems.value = normalizeScreeningHistory(screeningResult.value).map(normalizeScreeningEntry)
  } else {
    screeningItems.value = []
    loadWarnings.value.push('最近筛选')
    console.error('Failed to fetch screening history:', screeningResult.reason)
  }

  if (validationResult.status === 'fulfilled') {
    validationItems.value = normalizeList(validationResult.value).map(normalizeScreeningEntry)
  } else {
    validationItems.value = []
    loadWarnings.value.push('历史验证')
    console.error('Failed to fetch selection history:', validationResult.reason)
  }

  if (patternResult.status === 'fulfilled') {
    patternItems.value = normalizeList(patternResult.value).map(normalizePatternEntry)
  } else {
    patternItems.value = []
    loadWarnings.value.push('形态摘要')
    console.error('Failed to fetch pattern summary:', patternResult.reason)
  }

  if (taskHealthResult.status === 'fulfilled') {
    taskHealthBaselineTradeDate.value = String(taskHealthResult.value?.baseline_trade_date || '')
    taskAlertCount.value = coerceNumber(taskHealthResult.value?.alert_count)
    taskDatasets.value = normalizeList(taskHealthResult.value?.datasets).map(normalizeTaskDatasetStatus)
    taskAlerts.value = normalizeList(taskHealthResult.value?.alerts).map(normalizeTaskAlert)
  } else {
    taskHealthBaselineTradeDate.value = ''
    taskAlertCount.value = 0
    taskDatasets.value = []
    taskAlerts.value = []
    loadWarnings.value.push('任务健康')
    console.error('Failed to fetch task health summary:', taskHealthResult.reason)
  }

  lastSyncedAt.value = new Date().toISOString()
  loading.value = false
}

const loadRecentViewed = () => {
  try {
    const stored = localStorage.getItem('recently_viewed_stocks')
    if (stored) {
      recentViewedStocks.value = JSON.parse(stored).slice(0, 5)
    }
  } catch (e) {
    recentViewedStocks.value = []
  }
}

onMounted(() => {
  loadRecentViewed()
  refreshWorkbench()
})
</script>

<style scoped lang="scss">
.dashboard-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;

  h1 {
    margin: 6px 0 0;
    font-size: 30px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.92);
  }
}

.eyebrow {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8ba8ff;
}

.subtitle {
  max-width: 720px;
  margin: 10px 0 0;
  color: rgba(255, 255, 255, 0.58);
  line-height: 1.6;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.sync-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  min-width: 120px;

  strong {
    color: rgba(255, 255, 255, 0.88);
    font-size: 13px;
  }
}

.sync-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.44);
}

.refresh-btn {
  padding: 10px 16px;
  border: 1px solid rgba(122, 162, 255, 0.24);
  border-radius: 10px;
  background: rgba(41, 98, 255, 0.16);
  color: #dfe8ff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, opacity 0.2s ease;

  &:hover:not(:disabled) {
    background: rgba(41, 98, 255, 0.24);
    border-color: rgba(122, 162, 255, 0.4);
  }

  &:disabled {
    opacity: 0.65;
    cursor: wait;
  }
}

.warning-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  border: 1px solid rgba(255, 184, 77, 0.24);
  border-radius: 12px;
  background: rgba(255, 184, 77, 0.08);
  color: rgba(255, 235, 204, 0.88);

  span {
    color: rgba(255, 235, 204, 0.68);
  }
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.health-strip {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 18px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(18, 24, 38, 0.98), rgba(13, 18, 29, 0.98)),
    rgba(16, 19, 28, 0.92);
  box-shadow: 0 22px 40px rgba(0, 0, 0, 0.18);
}

.health-strip__header {
  align-items: center;
}

.health-strip__description {
  min-height: 0;
}

.health-strip__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.health-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.82);
}

.health-tag--stale {
  background: rgba(255, 184, 77, 0.12);
}

.health-tag--alert {
  background: rgba(255, 123, 123, 0.14);
}

.metric-strip--health {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.workbench-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 280px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(18, 24, 38, 0.98), rgba(13, 18, 29, 0.98)),
    rgba(16, 19, 28, 0.92);
  box-shadow: 0 22px 40px rgba(0, 0, 0, 0.18);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  h2 {
    margin: 4px 0 0;
    font-size: 22px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.92);
  }
}

.card-kicker {
  font-size: 12px;
  color: rgba(139, 168, 255, 0.88);
  letter-spacing: 0.04em;
}

.card-link {
  color: #c6d5ff;
  font-size: 13px;
  text-decoration: none;

  &:hover {
    color: #ffffff;
  }
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-strip--compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.metric-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
}

.metric-value {
  font-size: 26px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
}

.metric-value--small {
  font-size: 20px;
}

.metric-value--positive {
  color: #59d38c;
}

.metric-value--negative {
  color: #ff7b7b;
}

.metric-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.card-description {
  margin: 0;
  min-height: 44px;
  color: rgba(255, 255, 255, 0.64);
  line-height: 1.6;
}

.list-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: auto;
}

.list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  text-decoration: none;
  transition: background 0.2s ease, transform 0.2s ease;

  &:hover {
    background: rgba(41, 98, 255, 0.12);
    transform: translateY(-1px);
  }

  strong {
    display: block;
    color: rgba(255, 255, 255, 0.92);
    font-size: 15px;
  }

  span {
    color: rgba(255, 255, 255, 0.56);
    font-size: 13px;
  }
}

.row-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.signal-badge {
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
}

.signal-badge--bullish {
  background: rgba(89, 211, 140, 0.14);
  color: #72e2a1;
}

.signal-badge--neutral {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.72);
}

.signal-badge--bearish {
  background: rgba(255, 123, 123, 0.14);
  color: #ff9d9d;
}

@media (max-width: 1100px) {
  .page-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .sync-meta {
    align-items: flex-start;
  }

  .card-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .dashboard-page {
    padding: 18px;
  }

  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .metric-strip,
  .metric-strip--compact,
  .metric-strip--health {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.empty-hint {
  text-align: center;
  padding: 24px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
}
</style>
