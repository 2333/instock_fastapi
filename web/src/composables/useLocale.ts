import { computed, ref } from 'vue'

export type Locale = 'zh' | 'en'

const STORAGE_KEY = 'instock_locale'

const initial = (() => {
  if (typeof window === 'undefined') return 'zh' as Locale
  const saved = window.localStorage.getItem(STORAGE_KEY)
  return saved === 'en' ? 'en' : 'zh'
})()

const locale = ref<Locale>(initial)

const messages: Record<Locale, Record<string, string>> = {
  zh: {
    nav_dashboard: '仪表盘',
    nav_stocks: '股票',
    nav_patterns: '形态',
    nav_backtest: '回测',
    nav_selection: '选股',
    market_open: '交易中',
    market_closed: '休市',
    refresh: '刷新数据',
    settings: '设置',
    profile: '个人资料',
    preferences: '偏好设置',
    logout: '退出登录',
    user: '用户',
    lang_switch: 'EN',
    kline_default_title: 'K线图',
    label_open: '开盘',
    label_high: '最高',
    label_low: '最低',
    label_close: '收盘',
    label_volume: '成交量',
  },
  en: {
    nav_dashboard: 'Dashboard',
    nav_stocks: 'Stocks',
    nav_patterns: 'Patterns',
    nav_backtest: 'Backtest',
    nav_selection: 'Selection',
    market_open: 'Market Open',
    market_closed: 'Market Closed',
    refresh: 'Refresh Data',
    settings: 'Settings',
    profile: 'Profile',
    preferences: 'Preferences',
    logout: 'Logout',
    user: 'User',
    lang_switch: '中',
    kline_default_title: 'K-Line Chart',
    label_open: 'Open',
    label_high: 'High',
    label_low: 'Low',
    label_close: 'Close',
    label_volume: 'Volume',
  },
}

export function useLocale() {
  const setLocale = (value: Locale) => {
    locale.value = value
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, value)
    }
  }

  const toggleLocale = () => {
    setLocale(locale.value === 'zh' ? 'en' : 'zh')
  }

  const t = (key: string, fallback?: string) => {
    return messages[locale.value][key] || fallback || key
  }

  return {
    locale: computed(() => locale.value),
    setLocale,
    toggleLocale,
    t,
  }
}
