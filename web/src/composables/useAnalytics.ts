import { useRoute, type RouteLocationNormalized, type RouteLocationNormalizedLoaded } from 'vue-router'
import { authApi, eventsApi } from '@/api'

type RouteLike = Pick<RouteLocationNormalized, 'name' | 'path'> | Pick<RouteLocationNormalizedLoaded, 'name' | 'path'>

type DashboardCard = 'market' | 'attention' | 'selection' | 'backtest'
type AttentionAction = 'add' | 'remove' | 'update'
type AttentionSource = 'stock_detail' | 'attention_page'

interface AnalyticsEventPayload {
  event_type: 'page_view' | 'dashboard_card_click' | 'filter_run' | 'backtest_run' | 'pattern_view' | 'attention_action'
  page: string
  referrer?: string | null
  event_data?: Record<string, unknown> | null
}

let currentRouteReferrer: string | null = null

const compactString = (value: unknown, maxLength: number) => {
  if (value === null || value === undefined) return ''
  return String(value).trim().slice(0, maxLength)
}

const sanitizePath = (value: unknown) => {
  const path = compactString(value, 120)
  if (!path) return '/'
  return path.startsWith('/') ? path : `/${path}`
}

const sanitizeReferrer = (value: unknown) => {
  const referrer = compactString(value, 255)
  if (!referrer) return null
  return referrer.startsWith('/') ? referrer : `/${referrer}`
}

const sanitizeRouteName = (value: unknown) => compactString(value, 120) || 'unknown'

const sanitizeStringArray = (values: unknown, maxItems = 20, maxLength = 64) => {
  if (!Array.isArray(values)) return [] as string[]
  return Array.from(
    new Set(
      values
        .map((value) => compactString(value, maxLength))
        .filter(Boolean)
    )
  ).slice(0, maxItems)
}

const sanitizeInteger = (value: unknown, fallback = 0) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return fallback
  return Math.max(0, Math.round(numeric))
}

const sanitizeDate = (value: unknown) => {
  const normalized = compactString(value, 16)
  if (!normalized) return null
  if (/^\d{8}$/.test(normalized) || /^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
    return normalized
  }
  return null
}

const sanitizeStockCode = (value: unknown) => {
  const normalized = compactString(value, 24)
    .replace(/[^A-Za-z0-9._-]/g, '')
    .toUpperCase()
  return normalized || null
}

const getCurrentReferrer = () => currentRouteReferrer

export const setAnalyticsReferrer = (path?: string | null) => {
  currentRouteReferrer = sanitizeReferrer(path)
}

const dispatchEvent = (payload: AnalyticsEventPayload) => {
  if (!authApi.isAuthenticated()) return

  const run = () => {
    void eventsApi.track(payload).catch(() => undefined)
  }

  if (typeof queueMicrotask === 'function') {
    queueMicrotask(run)
    return
  }

  void Promise.resolve().then(run)
}

export const trackPageViewForRoute = (to: RouteLike, from?: RouteLike | null) => {
  const page = sanitizePath(to.path)
  const routeName = sanitizeRouteName(to.name)

  dispatchEvent({
    event_type: 'page_view',
    page,
    referrer: sanitizeReferrer(from?.path),
    event_data: {
      route_name: routeName,
    },
  })
}

export const useAnalytics = () => {
  const route = useRoute()

  const getPageContext = () => ({
    page: sanitizePath(route.path),
    referrer: getCurrentReferrer(),
  })

  const trackDashboardCardClick = (input: { card: DashboardCard; targetPath: string }) => {
    const { page, referrer } = getPageContext()
    const targetPath = sanitizePath(input.targetPath)

    dispatchEvent({
      event_type: 'dashboard_card_click',
      page,
      referrer,
      event_data: {
        card: input.card,
        target_path: targetPath,
      },
    })
  }

  const trackFilterRun = (input: {
    filterKeys: string[]
    market?: string | null
    resultCount: number
    tradeDate?: string | null
  }) => {
    const { page, referrer } = getPageContext()
    const filterKeys = sanitizeStringArray(input.filterKeys)

    dispatchEvent({
      event_type: 'filter_run',
      page,
      referrer,
      event_data: {
        filter_keys: filterKeys,
        filter_count: filterKeys.length,
        market: compactString(input.market, 32) || null,
        result_count: sanitizeInteger(input.resultCount),
        trade_date: sanitizeDate(input.tradeDate),
      },
    })
  }

  const trackBacktestRun = (input: {
    strategy: string
    stockCode: string
    period: string
    startDate: string
    endDate: string
    paramKeys: string[]
  }) => {
    const { page, referrer } = getPageContext()
    const strategy = compactString(input.strategy, 64)
    const stockCode = sanitizeStockCode(input.stockCode)
    const period = compactString(input.period, 32)
    const startDate = sanitizeDate(input.startDate)
    const endDate = sanitizeDate(input.endDate)

    if (!strategy || !stockCode || !period || !startDate || !endDate) {
      return
    }

    dispatchEvent({
      event_type: 'backtest_run',
      page,
      referrer,
      event_data: {
        strategy,
        stock_code: stockCode,
        period,
        start_date: startDate,
        end_date: endDate,
        param_keys: sanitizeStringArray(input.paramKeys),
      },
    })
  }

  const trackPatternView = (input: {
    stockCode: string
    patternName: string
    patternType: string
    confidence: number
    tradeDate: string
  }) => {
    const { page, referrer } = getPageContext()
    const stockCode = sanitizeStockCode(input.stockCode)
    const patternName = compactString(input.patternName, 80)
    const patternType = compactString(input.patternType, 48)
    const tradeDate = sanitizeDate(input.tradeDate)

    if (!stockCode || !patternName || !patternType || !tradeDate) {
      return
    }

    dispatchEvent({
      event_type: 'pattern_view',
      page,
      referrer,
      event_data: {
        stock_code: stockCode,
        pattern_name: patternName,
        pattern_type: patternType,
        confidence: sanitizeInteger(input.confidence),
        trade_date: tradeDate,
      },
    })
  }

  const trackAttentionAction = (input: {
    action: AttentionAction
    stockCode: string
    source: AttentionSource
  }) => {
    const { page, referrer } = getPageContext()
    const stockCode = sanitizeStockCode(input.stockCode)

    if (!stockCode) {
      return
    }

    dispatchEvent({
      event_type: 'attention_action',
      page,
      referrer,
      event_data: {
        action: input.action,
        stock_code: stockCode,
        source: input.source,
      },
    })
  }

  return {
    trackAttentionAction,
    trackBacktestRun,
    trackDashboardCardClick,
    trackFilterRun,
    trackPatternView,
  }
}
