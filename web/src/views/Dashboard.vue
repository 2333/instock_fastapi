<template>
  <div class="dashboard-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Phase 0b 工作台</p>
        <h1>四个入口，把扫描、关注、验证收回来</h1>
        <p class="subtitle">
          首页只保留真实入口：市场温度计、我的关注、今日扫描发现、策略信号与回测更新。
        </p>
      </div>
      <div class="header-actions">
        <div class="sync-meta">
          <span class="sync-label">最近刷新</span>
          <strong>{{ lastSyncedLabel }}</strong>
        </div>
        <button class="refresh-btn" :disabled="loading" @click="refreshWorkbench">
          {{ loading ? '刷新中...' : '刷新工作台' }}
        </button>
      </div>
    </header>

    <div v-if="loadWarnings.length" class="warning-banner">
      <strong>部分数据暂不可用</strong>
      <span>{{ loadWarnings.join(' / ') }}</span>
    </div>

    <div class="card-grid">
      <section class="workbench-card workbench-card--market">
        <div class="card-header">
          <div>
            <span class="card-kicker">市场温度计</span>
            <h2>盘后市场概览</h2>
            <span v-if="marketSummary.tradeDate" class="card-date">数据日期：{{ formatTradeDate(marketSummary.tradeDate) }}</span>
          </div>
          <router-link to="/stocks" class="card-link">查看股票列表</router-link>
        </div>

        <div class="metric-strip metric-strip--market">
          <div class="metric-block">
            <span class="metric-value metric-value--positive">{{ formatCount(marketSummary.advancers) }}</span>
            <span class="metric-label">上涨家数</span>
          </div>
          <div class="metric-block">
            <span class="metric-value metric-value--negative">{{ formatCount(marketSummary.decliners) }}</span>
            <span class="metric-label">下跌家数</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ formatCount(marketSummary.unchanged) }}</span>
            <span class="metric-label">平盘家数</span>
          </div>
          <div class="metric-block">
            <span class="metric-value metric-value--positive">{{ formatCount(marketSummary.limitUp) }}</span>
            <span class="metric-label">涨停</span>
          </div>
          <div class="metric-block">
            <span class="metric-value metric-value--negative">{{ formatCount(marketSummary.limitDown) }}</span>
            <span class="metric-label">跌停</span>
          </div>
        </div>

        <div class="mood-panel">
          <div class="mood-panel__header">
            <span class="card-kicker">情绪摘要</span>
            <span :class="toneBadgeClass(marketSummary.moodTone)">{{ marketSummary.moodLabel }}</span>
          </div>
          <p class="card-description">
            <template v-if="marketSummary.headline">
              {{ marketSummary.headline }}
            </template>
            <template v-else-if="marketSummary.tradeDate">
              已完成 {{ formatDisplayDate(marketSummary.tradeDate) }} 的市场聚合，等待后端补充情绪摘要。
            </template>
            <template v-else>
              市场温度计暂未返回数据，刷新后会自动回落为空状态。
            </template>
          </p>
        </div>

        <div v-if="marketSummary.majorIndices.length" class="list-stack">
          <div
            v-for="indexItem in marketSummary.majorIndices"
            :key="indexItem.code"
            class="list-row list-row--static"
          >
            <div>
              <strong>{{ indexItem.name }}</strong>
              <span>{{ indexItem.code }}</span>
            </div>
            <div class="row-meta">
              <span :class="trendBadgeClass(indexItem.changeRate)">
                {{ formatSignedPercent(indexItem.changeRate) }}
              </span>
              <span class="row-note">
                {{ indexItem.current !== null ? formatCount(indexItem.current) : formatIndexMeta(indexItem) }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="workbench-card">
        <div class="card-header">
          <div>
            <span class="card-kicker">我的关注</span>
            <h2>关注列表联动</h2>
          </div>
          <router-link to="/attention" class="card-link">管理关注</router-link>
        </div>

        <div class="metric-strip metric-strip--compact">
          <div class="metric-block">
            <span class="metric-value">{{ attentionItems.length }}</span>
            <span class="metric-label">关注股票</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ triggeredAttentionCount }}</span>
            <span class="metric-label">今日命中</span>
          </div>
          <div class="metric-block">
            <span class="metric-value metric-value--small">{{ attentionLatestDateLabel }}</span>
            <span class="metric-label">最近加入</span>
          </div>
        </div>

        <p class="card-description">
          <template v-if="triggeredAttentionCount > 0">
            今日扫描结果已和关注列表联动，命中的个股会直接标记出来，方便继续核对验证。
          </template>
          <template v-else-if="attentionItems.length > 0">
            关注列表已加载，但当前暂无命中提示。后端补上今日扫描概要后，这里会自动点亮。
          </template>
          <template v-else>
            还没有关注股票，可以从个股详情或关注页补充观察名单。
          </template>
        </p>

        <div v-if="attentionItems.length" class="list-stack">
          <router-link
            v-for="item in topAttentionItems"
            :key="item.code"
            :to="buildStockLink(item.code, todaySummary.tradeDate)"
            class="list-row"
          >
            <div>
              <strong>{{ item.code }}</strong>
              <span>{{ item.name }}</span>
            </div>
            <div class="row-meta">
              <span v-if="isAttentionTriggered(item.code)" class="signal-badge signal-badge--bullish">
                今日命中
              </span>
              <span>{{ formatDisplayDate(item.createdAt) }}</span>
            </div>
          </router-link>
        </div>
      </section>

      <section class="workbench-card">
        <div class="card-header">
          <div>
            <span class="card-kicker">今日扫描发现</span>
            <h2>已保存条件的命中概要</h2>
            <span v-if="todaySummary.tradeDate" class="card-date">数据日期：{{ formatTradeDate(todaySummary.tradeDate) }}</span>
          </div>
          <router-link to="/selection" class="card-link">进入筛选页</router-link>
        </div>

        <div class="metric-strip metric-strip--compact">
          <div class="metric-block">
            <span class="metric-value">{{ formatCount(todaySummary.savedConditionCount) }}</span>
            <span class="metric-label">已保存条件</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ formatCount(todaySummary.totalHits) }}</span>
            <span class="metric-label">今日命中</span>
          </div>
          <div class="metric-block">
            <span class="metric-value metric-value--small">{{ todaySummaryDateLabel }}</span>
            <span class="metric-label">筛选交易日</span>
          </div>
        </div>

        <p class="card-description">
          <template v-if="todaySummary.note">
            {{ todaySummary.note }}
          </template>
          <template v-else-if="todaySummary.items.length > 0">
            今天命中的条件已经按保存列表聚合，点开筛选页可以继续回看命中股票和证据。
          </template>
          <template v-else>
            还没有可展示的今日扫描概要，等待后端把今日摘要接口接上后会自动显示。
          </template>
        </p>

        <div v-if="todaySummary.items.length" class="list-stack">
          <router-link
            v-for="item in topTodayConditions"
            :key="item.id"
            to="/selection"
            class="list-row"
          >
            <div>
              <strong>{{ item.name }}</strong>
              <span>{{ item.category || '保存条件' }}</span>
            </div>
            <div class="row-meta">
              <span class="row-note">{{ item.hitCount }} 只</span>
              <span>{{ item.topCodes.length ? item.topCodes.slice(0, 2).join(' / ') : '暂无代码' }}</span>
            </div>
          </router-link>
        </div>
      </section>

      <section class="workbench-card">
        <div class="card-header">
          <div>
            <span class="card-kicker">策略信号 / 回测更新</span>
            <h2>最近回测与策略记录</h2>
            <span v-if="latestBacktest?.createdAt" class="card-date">最近回测：{{ formatDate(latestBacktest.createdAt) }}</span>
          </div>
          <router-link to="/backtest" class="card-link">查看回测页</router-link>
        </div>

        <div class="metric-strip metric-strip--compact">
          <div class="metric-block">
            <span class="metric-value">{{ backtestSummary.totalReturnLabel }}</span>
            <span class="metric-label">最新收益</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ backtestSummary.drawdownLabel }}</span>
            <span class="metric-label">最大回撤</span>
          </div>
          <div class="metric-block">
            <span class="metric-value">{{ backtestSummary.winRateLabel }}</span>
            <span class="metric-label">胜率</span>
          </div>
        </div>

        <p class="card-description">
          <template v-if="latestBacktest">
            最新回测来自 {{ latestBacktest.strategyLabel }}，覆盖 {{ latestBacktest.rangeLabel }}。
          </template>
          <template v-else-if="backtestItems.length > 0">
            已加载回测历史，但暂未解析出最新摘要。
          </template>
          <template v-else>
            暂无回测记录，进入回测页后可直接发起新的策略验证。
          </template>
        </p>

        <div v-if="backtestItems.length" class="list-stack">
          <router-link
            v-for="item in topBacktestItems"
            :key="item.id"
            :to="buildBacktestLink(item)"
            class="list-row"
          >
            <div>
              <strong>{{ item.name }}</strong>
              <span>{{ item.strategyLabel }}</span>
            </div>
            <div class="row-meta">
              <span :class="trendBadgeClass(item.totalReturn)">
                {{ formatSignedPercent(item.totalReturn) }}
              </span>
              <span>{{ formatDisplayDate(item.createdAt) }}</span>
            </div>
          </router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { attentionApi, backtestApi, marketApi, selectionApi } from '@/api'

interface AttentionEntry {
  code: string
  name: string
  group: string
  notes: string
  createdAt: string
}

interface MarketIndexEntry {
  code: string
  name: string
  current: number | null
  changeRate: number | null
  constituentCount: number | null
  source: string
}

interface MarketSummaryState {
  tradeDate: string
  advancers: number | null
  decliners: number | null
  unchanged: number | null
  limitUp: number | null
  limitDown: number | null
  headline: string
  moodLabel: string
  moodTone: 'bullish' | 'neutral' | 'bearish'
  majorIndices: MarketIndexEntry[]
}

interface TodayConditionEntry {
  id: string
  name: string
  category: string
  hitCount: number
  tradeDate: string
  summary: string
  topCodes: string[]
}

interface TodaySummaryState {
  tradeDate: string
  totalHits: number | null
  savedConditionCount: number | null
  note: string
  items: TodayConditionEntry[]
  triggeredCodes: string[]
}

interface BacktestEntry {
  id: string
  name: string
  strategy: string
  strategyLabel: string
  code: string
  stockName: string
  createdAt: string
  startDate: string
  endDate: string
  rangeLabel: string
  totalReturn: number
  annualReturn: number
  maxDrawdown: number
  winRate: number
  totalTrades: number
}

const loading = ref(false)
const lastSyncedAt = ref('')
const loadWarnings = ref<string[]>([])

const attentionItems = ref<AttentionEntry[]>([])
const marketSummary = ref<MarketSummaryState>({
  tradeDate: '',
  advancers: null,
  decliners: null,
  unchanged: null,
  limitUp: null,
  limitDown: null,
  headline: '',
  moodLabel: '待更新',
  moodTone: 'neutral',
  majorIndices: [],
})
const todaySummary = ref<TodaySummaryState>({
  tradeDate: '',
  totalHits: null,
  savedConditionCount: null,
  note: '',
  items: [],
  triggeredCodes: [],
})
const backtestItems = ref<BacktestEntry[]>([])

const unwrapPayload = (value: unknown) => {
  if (value && typeof value === 'object' && 'data' in value) {
    return (value as { data?: unknown }).data ?? value
  }
  return value
}

const asObject = (value: unknown): Record<string, any> => {
  const payload = unwrapPayload(value)
  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    return payload as Record<string, any>
  }
  return {}
}

const asArray = (value: unknown): any[] => {
  const payload = unwrapPayload(value)
  if (Array.isArray(payload)) return payload
  if (payload && typeof payload === 'object') {
    const candidates = ['items', 'list', 'results', 'data']
    for (const key of candidates) {
      const candidate = (payload as Record<string, unknown>)[key]
      if (Array.isArray(candidate)) return candidate
    }
  }
  return []
}

const toNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

const toNullableNumber = (value: unknown) => {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const toString = (value: unknown, fallback = '') => {
  if (value === null || value === undefined) return fallback
  return String(value)
}

const formatDisplayDate = (value?: string | null) => {
  if (!value) return '--'
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value
  if (/^\d{8}$/.test(value)) return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

const formatTradeDate = (value?: string | null) => {
  if (!value) return '--'
  if (/^\d{8}$/.test(value)) return `${value.slice(0, 4)}/${value.slice(4, 6)}/${value.slice(6, 8)}`
  return value
}

const formatDate = (value?: string | null) => {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

const formatCount = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '--'
  return new Intl.NumberFormat('zh-CN').format(value)
}

const formatPercent = (value: unknown, digits = 1) => {
  const numeric = toNumber(value, Number.NaN)
  if (Number.isNaN(numeric)) return '--'
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(digits)}%`
}

const formatSignedPercent = (value: unknown, digits = 1) => {
  const numeric = toNumber(value, Number.NaN)
  if (Number.isNaN(numeric)) return '--'
  return `${numeric > 0 ? '+' : ''}${numeric.toFixed(digits)}%`
}

const toneBadgeClass = (tone: 'bullish' | 'neutral' | 'bearish') => {
  if (tone === 'bullish') return 'signal-badge signal-badge--bullish'
  if (tone === 'bearish') return 'signal-badge signal-badge--bearish'
  return 'signal-badge signal-badge--neutral'
}

const trendBadgeClass = (value: unknown) => {
  if (value === null || value === undefined || value === '') return 'signal-badge signal-badge--neutral'
  const numeric = toNumber(value, 0)
  if (numeric > 0) return 'signal-badge signal-badge--bullish'
  if (numeric < 0) return 'signal-badge signal-badge--bearish'
  return 'signal-badge signal-badge--neutral'
}

const formatIndexMeta = (item: MarketIndexEntry) => {
  if (item.constituentCount !== null) {
    return `成分 ${formatCount(item.constituentCount)}`
  }
  if (item.source === 'proxy') return '代理口径'
  if (item.source === 'fallback') return '待补数'
  return '--'
}

const normalizeAttentionEntry = (item: any): AttentionEntry => ({
  code: toString(item?.code || item?.symbol || item?.ts_code?.split?.('.')?.[0] || ''),
  name: toString(item?.stock_name || item?.name || item?.code || '--'),
  group: toString(item?.group || 'watch'),
  notes: toString(item?.notes || ''),
  createdAt: toString(item?.created_at || item?.createdAt || ''),
})

const normalizeMarketSummary = (response: unknown): MarketSummaryState => {
  const payload = asObject(response)
  const counts = payload.counts && typeof payload.counts === 'object' ? payload.counts : payload
  const indicesSource = asArray(payload.indices || payload.major_indices || payload.majorIndices || payload.indexes)

  const tradeDate = toString(
    payload.trade_date || payload.tradeDate || payload.date || counts.trade_date || counts.date || '',
  )
  const advancers = toNullableNumber(
    payload.advancers ?? counts.advancers ?? payload.up_count ?? counts.up_count ?? payload.rise_count ?? counts.rise_count,
  )
  const decliners = toNullableNumber(
    payload.decliners ?? counts.decliners ?? payload.down_count ?? counts.down_count ?? payload.fall_count ?? counts.fall_count,
  )
  const unchanged = toNullableNumber(
    payload.unchanged ?? counts.unchanged ?? payload.flat_count ?? counts.flat_count ?? payload.neutral_count ?? counts.neutral_count,
  )
  const limitUp = toNullableNumber(
    payload.limit_up ?? counts.limit_up ?? payload.limitUp ?? counts.limitUp ?? payload.limit_up_count ?? counts.limit_up_count,
  )
  const limitDown = toNullableNumber(
    payload.limit_down ?? counts.limit_down ?? payload.limitDown ?? counts.limitDown ?? payload.limit_down_count ?? counts.limit_down_count,
  )

  const majorIndices = indicesSource.slice(0, 5).map((item: any) => ({
    code: toString(item?.code || item?.symbol || item?.index_code || item?.ts_code || ''),
    name: toString(item?.name || item?.index_name || item?.label || '指数'),
    current: toNullableNumber(item?.current ?? item?.close ?? item?.value ?? item?.last),
    changeRate: toNullableNumber(item?.change_rate ?? item?.pct_chg ?? item?.rate ?? item?.changeRate),
    constituentCount: toNullableNumber(item?.constituent_count ?? item?.constituentCount ?? item?.sample_size),
    source: toString(item?.source || 'unknown'),
  }))

  const headline = toString(
    payload.headline ||
      payload.summary ||
      payload.mood_summary ||
      payload.sentiment_summary ||
      payload.description ||
      '',
  )

  const sentiment = toString(payload.mood || payload.tone || '').toLowerCase()
  const advancerValue = advancers ?? 0
  const declinerValue = decliners ?? 0
  const moodTone: 'bullish' | 'neutral' | 'bearish' =
    sentiment.includes('bull') || sentiment.includes('强') || sentiment.includes('热')
      ? 'bullish'
      : sentiment.includes('bear') || sentiment.includes('弱') || sentiment.includes('冷')
        ? 'bearish'
        : advancerValue > declinerValue
          ? 'bullish'
          : declinerValue > advancerValue
            ? 'bearish'
            : 'neutral'

  const moodLabel = toString(payload.mood_label || payload.moodLabel || payload.sentiment_label || '').trim() || (() => {
    if (moodTone === 'bullish') return '偏强'
    if (moodTone === 'bearish') return '偏弱'
    return '中性'
  })()

  return {
    tradeDate,
    advancers,
    decliners,
    unchanged,
    limitUp,
    limitDown,
    headline,
    moodLabel,
    moodTone,
    majorIndices,
  }
}

const normalizeTodaySummary = (response: unknown): TodaySummaryState => {
  const payload = asObject(response)
  const rawItems = asArray(
    payload.items ||
      payload.conditions ||
      payload.saved_conditions ||
      payload.condition_hits ||
      payload.results ||
      payload.data,
  )

  const items = rawItems.map((item: any, index) => {
    const topCodes = [
      ...asArray(item?.top_codes || item?.codes || item?.matched_codes || item?.top_matches || item?.hits),
      ...asArray(item?.stocks),
    ]
      .map((code) => toString(code?.code || code?.symbol || code?.ts_code?.split?.('.')?.[0] || code))
      .filter(Boolean)

    return {
      id: toString(item?.id || item?.condition_id || item?.name || `condition-${index}`),
      name: toString(item?.name || item?.condition_name || item?.label || '未命名条件'),
      category: toString(item?.category || item?.group || item?.type || ''),
      hitCount: toNumber(item?.hit_count ?? item?.total ?? item?.count ?? item?.matches ?? topCodes.length),
      tradeDate: toString(item?.trade_date || payload.trade_date || payload.date || ''),
      summary: toString(item?.summary || item?.reason_summary || item?.note || ''),
      topCodes,
    } as TodayConditionEntry
  })

  const triggeredCodes = new Set<string>()
  const topLevelCodeSources = [
    payload.triggered_codes,
    payload.matched_codes,
    payload.matched_codes_today,
    payload.watchlist_hits,
    payload.codes,
    payload.symbols,
  ]
  for (const source of topLevelCodeSources) {
    for (const code of asArray(source)) {
      const normalized = toString(code?.code || code?.symbol || code?.ts_code?.split?.('.')?.[0] || code)
      if (normalized) triggeredCodes.add(normalized)
    }
  }
  for (const item of items) {
    for (const code of item.topCodes) triggeredCodes.add(code)
  }

  const hasMeaningfulPayload = Object.keys(payload).length > 0 || rawItems.length > 0
  const totalHits =
    toNullableNumber(
      payload.total ?? payload.total_hits ?? payload.hit_count ?? payload.matches ?? payload.hits,
    ) ?? (hasMeaningfulPayload ? items.reduce((sum, item) => sum + item.hitCount, 0) : null)
  const savedConditionCount =
    toNullableNumber(
      payload.saved_condition_count ?? payload.condition_count ?? payload.conditions_count ?? payload.total_conditions,
    ) ?? (hasMeaningfulPayload ? items.length : null)
  const note = toString(payload.note || payload.summary || payload.message || '')
  const tradeDate = toString(payload.trade_date || payload.tradeDate || payload.date || items[0]?.tradeDate || '')

  return {
    tradeDate,
    totalHits,
    savedConditionCount,
    note,
    items,
    triggeredCodes: Array.from(triggeredCodes),
  }
}

const normalizeBacktestEntry = (item: any): BacktestEntry => {
  const strategy = toString(item?.strategy || item?.meta?.strategy || item?.name || 'backtest')
  const startDate = toString(item?.start_date || item?.startDate || '')
  const endDate = toString(item?.end_date || item?.endDate || '')

  return {
    id: toString(item?.id || item?.backtest_id || `${strategy}-${startDate}-${endDate}`),
    name: toString(item?.name || item?.title || strategy),
    strategy,
    strategyLabel: toString(item?.strategy_label || item?.strategyLabel || strategy),
    code: toString(item?.code || item?.stock_code || item?.symbol || ''),
    stockName: toString(item?.stock_name || item?.stockName || ''),
    createdAt: toString(item?.created_at || item?.createdAt || ''),
    startDate,
    endDate,
    rangeLabel: startDate && endDate ? `${formatDisplayDate(startDate)} → ${formatDisplayDate(endDate)}` : '未提供区间',
    totalReturn: toNumber(item?.total_return ?? item?.summary?.total_return ?? 0),
    annualReturn: toNumber(item?.annual_return ?? item?.summary?.annual_return ?? 0),
    maxDrawdown: toNumber(item?.max_drawdown ?? item?.summary?.max_drawdown ?? 0),
    winRate: toNumber(item?.win_rate ?? item?.summary?.win_rate ?? 0),
    totalTrades: toNumber(item?.total_trades ?? item?.summary?.total_trades ?? 0),
  }
}

const attentionLatestDateLabel = computed(() => {
  const latest = attentionItems.value[0]?.createdAt
  return latest ? formatDisplayDate(latest) : '--'
})

const triggeredAttentionCount = computed(() => {
  if (!attentionItems.value.length) return 0
  return attentionItems.value.filter((item) => isAttentionTriggered(item.code)).length
})

const topAttentionItems = computed(() => attentionItems.value.slice(0, 4))

const topTodayConditions = computed(() =>
  [...todaySummary.value.items]
    .sort((a, b) => b.hitCount - a.hitCount || a.name.localeCompare(b.name))
    .slice(0, 4),
)

const todaySummaryDateLabel = computed(() => formatDisplayDate(todaySummary.value.tradeDate))

const latestBacktest = computed(() => backtestItems.value[0] || null)

const topBacktestItems = computed(() => backtestItems.value.slice(0, 3))

const backtestSummary = computed(() => {
  const latest = latestBacktest.value
  return {
    totalReturnLabel: latest ? formatSignedPercent(latest.totalReturn) : '--',
    drawdownLabel: latest ? formatSignedPercent(latest.maxDrawdown) : '--',
    winRateLabel: latest ? formatPercent(latest.winRate) : '--',
  }
})

const lastSyncedLabel = computed(() => {
  if (!lastSyncedAt.value) return '--'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(lastSyncedAt.value))
})

const buildStockLink = (code: string, screeningDate?: string) => ({
  path: `/stock/${code}`,
  query: screeningDate ? { screening_date: screeningDate } : undefined,
})

const buildBacktestLink = (item: BacktestEntry) => ({
  path: '/backtest',
  query: item.id ? { backtest_id: item.id } : undefined,
})

const isAttentionTriggered = (code: string) => {
  return todaySummary.value.triggeredCodes.includes(code)
}

function refreshWorkbench() {
  loading.value = true
  loadWarnings.value = []

  return Promise.allSettled([
    marketApi.getSummary(),
    attentionApi.getList(),
    selectionApi.getTodaySummary({ limit: 12 }),
    backtestApi.getBacktestHistory(5),
  ])
    .then(([marketResult, attentionResult, todayResult, backtestResult]) => {
      if (marketResult.status === 'fulfilled') {
        marketSummary.value = normalizeMarketSummary(marketResult.value)
      } else {
        marketSummary.value = {
          tradeDate: '',
          advancers: null,
          decliners: null,
          unchanged: null,
          limitUp: null,
          limitDown: null,
          headline: '',
          moodLabel: '待更新',
          moodTone: 'neutral',
          majorIndices: [],
        }
        loadWarnings.value.push('市场温度计')
      }

      if (attentionResult.status === 'fulfilled') {
        attentionItems.value = asArray(attentionResult.value)
          .map(normalizeAttentionEntry)
          .filter((item: AttentionEntry) => Boolean(item.code))
      } else {
        attentionItems.value = []
        loadWarnings.value.push('我的关注')
      }

      if (todayResult.status === 'fulfilled') {
        todaySummary.value = normalizeTodaySummary(todayResult.value)
      } else {
        todaySummary.value = {
          tradeDate: '',
          totalHits: null,
          savedConditionCount: null,
          note: '',
          items: [],
          triggeredCodes: [],
        }
        loadWarnings.value.push('今日扫描发现')
      }

      if (backtestResult.status === 'fulfilled') {
        backtestItems.value = asArray(backtestResult.value)
          .map(normalizeBacktestEntry)
          .sort((a: BacktestEntry, b: BacktestEntry) => b.createdAt.localeCompare(a.createdAt))
      } else {
        backtestItems.value = []
        loadWarnings.value.push('策略信号 / 回测更新')
      }

      lastSyncedAt.value = new Date().toISOString()
    })
    .finally(() => {
      loading.value = false
    })
}

onMounted(() => {
  refreshWorkbench()
})
</script>

<style scoped lang="scss">
.dashboard-page {
  padding: 24px;
  position: relative;
  isolation: isolate;

  &::before {
    content: '';
    position: absolute;
    inset: -18px -18px auto;
    height: 300px;
    z-index: -1;
    background:
      radial-gradient(circle at 20% 20%, rgba(88, 121, 255, 0.22), transparent 34%),
      radial-gradient(circle at 80% 0%, rgba(47, 207, 133, 0.12), transparent 28%),
      linear-gradient(180deg, rgba(18, 24, 38, 0.94), rgba(13, 18, 29, 0.66));
    filter: blur(8px);
    pointer-events: none;
  }
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

.card-date {
  display: block;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  margin-top: 2px;
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
  gap: 12px;
}

.metric-strip--market {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.metric-strip--compact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
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

.mood-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
}

.mood-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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

.list-row--static {
  cursor: default;

  &:hover {
    transform: none;
  }
}

.row-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.row-note {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
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

  .metric-strip--market,
  .metric-strip--compact {
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
