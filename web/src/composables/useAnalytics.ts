/**
 * 用户行为分析 Composable
 * 用于追踪关键用户操作，支持匿名与登录用户
 */
export interface TrackEventOptions {
  event_type: string
  event_data?: Record<string, any>
  page?: string
  referrer?: string
}

export const useAnalytics = () => {
  const track = (options: TrackEventOptions) => {
    // 不阻塞主流程，静默发送
    const payload = {
      event_type: options.event_type,
      event_data: options.event_data,
      page: options.page || window.location.pathname,
      referrer: options.referrer || document.referrer,
    }

    fetch('/api/v1/events/track', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).catch(() => {
      // 静默失败，不影响用户体验
    })
  }

  // 常用事件快捷方法
  const pageView = (page?: string) => {
    track({ event_type: 'page_view', page })
  }

  const filterRun = (criteria: Record<string, any>, resultCount: number, durationMs: number) => {
    track({
      event_type: 'filter_run',
      event_data: { criteria, result_count: resultCount, duration_ms: durationMs },
      page: '/selection',
    })
  }

  const backtestRun = (params: Record<string, any>, async: boolean = false) => {
    track({
      event_type: 'backtest_run',
      event_data: { ...params, async },
      page: '/backtest',
    })
  }

  const patternView = (patternName: string, confidence: number, tradeDate: string, patternKey?: string) => {
    track({
      event_type: 'pattern_view',
      event_data: { pattern_name: patternName, confidence, trade_date: tradeDate, pattern_key: patternKey },
      page: '/stock',
    })
  }

  const attentionAction = (action: 'add' | 'remove', code: string, source?: string) => {
    track({
      event_type: 'attention_action',
      event_data: { action, code, source },
      page: '/dashboard',
    })
  }

  return {
    track,
    pageView,
    filterRun,
    backtestRun,
    patternView,
    attentionAction,
  }
}
