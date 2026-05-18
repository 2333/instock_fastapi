import { computed, ref } from 'vue'

export type Locale = 'zh' | 'en'

const STORAGE_KEY = 'instock_locale'

export const normalizeLocale = (value: unknown): Locale => {
  if (typeof value === 'string' && value.toLowerCase().startsWith('en')) {
    return 'en'
  }
  return 'zh'
}

const readStoredLocale = (): Locale => {
  if (typeof window === 'undefined') return 'zh'

  try {
    return normalizeLocale(window.localStorage.getItem(STORAGE_KEY))
  } catch {
    return 'zh'
  }
}

const persistLocale = (value: Locale) => {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(STORAGE_KEY, value)
  } catch {
    // Some browsers or privacy modes can block localStorage writes.
  }
}

const syncDocumentLocale = (value: Locale) => {
  if (typeof document === 'undefined') return

  document.documentElement.lang = value === 'en' ? 'en' : 'zh-CN'
  document.documentElement.setAttribute('data-locale', value)
}

const locale = ref<Locale>(readStoredLocale())
syncDocumentLocale(locale.value)

const messages: Record<Locale, Record<string, string>> = {
  zh: {
    nav_home: '首页',
    nav_workspace: '工作台',
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
    sidebar_watchlist: '自选股',
    sidebar_watchlist_empty: '暂无关注股票',
    sidebar_quick_actions: '快捷操作',
    sidebar_add_stock: '添加股票',
    sidebar_refresh_all: '刷新全部',
    sidebar_add_watchlist: '添加自选股',
    sidebar_add_placeholder: '输入股票代码 (例如: 600519)',
    sidebar_add_submit: '添加',
    sidebar_cancel: '取消',
    sidebar_watchlist_refreshed: '关注列表已刷新',
    sidebar_load_failed: '加载关注列表失败',
    sidebar_added_prefix: '已添加',
    sidebar_added_suffix: '到关注列表',
    sidebar_add_failed: '添加关注失败',
    kline_default_title: 'K线图',
    label_open: '开盘',
    label_high: '最高',
    label_low: '最低',
    label_close: '收盘',
    label_volume: '成交量',
    period_1min: '1分',
    period_5min: '5分',
    period_15min: '15分',
    period_day: '日',
    period_week: '周',
    period_month: '月',
    adjust_bfq: '不复权',
    adjust_qfq: '前复权',
    adjust_hfq: '后复权',
    hint_not_available: '暂未接入',
    no_data_prefix: '暂无',
    no_data_suffix: 'K线数据',
    no_period_data_suffix: '级别数据',
    stock_loading: '加载中...',
    stock_not_found: '未找到股票信息',
    stock_market_sh: '上海',
    stock_market_sz: '深圳',
    stock_market_bj: '北交所',
    stock_chart_native: '业务图表',
    stock_chart_tv: 'TradingView',
    stock_chart_native_desc: '使用站内行情、复权与现有指标逻辑。',
    stock_chart_tv_desc: '使用 TradingView 内置行情与指标，作为补充分析视图。',
    stock_profile: '股票概况',
    stock_open: '开盘价',
    stock_high: '最高价',
    stock_low: '最低价',
    stock_turnover: '成交额',
    stock_industry: '所属行业',
    stock_list_date: '上市日期',
    stock_actions: '快速操作',
    stock_backtest: '回测策略',
    stock_watch_add: '添加到关注',
    stock_watch_remove: '取消关注',
    stock_analyze_patterns: '分析形态',
    stock_related_patterns: '相关形态',
    stock_no_patterns: '暂无形态数据',
    stock_pattern_range_label: '评估时间范围',
    stock_pattern_range_current: '当前K线窗口',
    stock_pattern_range_focus: '评估区间',
    stock_pattern_marks_show: '显示形态标记',
    stock_pattern_marks_hide: '隐藏形态标记',
    stock_pattern_focus_range: '聚焦评估区间',
    stock_pattern_records: '条记录',
    stock_pattern_link_hint: '悬浮或聚焦时会联动 K 线',
    stock_tv_pattern_note: '列表仍来自站内形态识别；TradingView 视图不会直接显示这些业务标记。',
    stock_adjust_fallback: '当前复权数据暂不可用，已自动回退为不复权数据',
    tv_footer_prefix: '行情与内置指标由 TradingView 提供，和站内复权与形态识别独立。',
    tv_open_full_chart: '打开完整图表',
    tv_no_symbol: '当前股票暂未映射到 TradingView 代码，无法展示高级分析视图。',
    tv_data_level_a_share: '当前 A 股 widget 数据级别以日线为主，小时/分钟级别通常不可用。',
    tv_data_level_bj: '北交所符号在 TradingView widget 中的覆盖度需要逐个标的验证。',
    login_tagline: '智能股票分析平台',
    login_username: '用户名',
    login_username_placeholder: '请输入用户名',
    login_password: '密码',
    login_password_placeholder: '请输入密码',
    login_submit: '登录',
    login_submitting: '登录中...',
    login_error_default: '登录失败，请检查用户名和密码',
    login_register_prompt: '还没有账号?',
    login_register_link: '立即注册',
    register_title: '注册新账号',
    register_email: '邮箱',
    register_email_placeholder: '请输入邮箱',
    register_submit: '注册',
    register_submitting: '注册中...',
    register_cancel: '取消',
    register_success: '注册成功，请登录',
    register_error_default: '注册失败',
    settings_page_title: '设置',
    settings_page_subtitle: '仅展示当前已经接入并会生效的偏好设置',
    settings_current_section: '当前可配置',
    settings_language_label: '语言',
    settings_language_help: '切换界面语言，并同步到账户设置。',
    settings_default_home_label: '默认首页',
    settings_default_home_help: '当前主线入口固定为首页工作台，`/workspace` 不再作为默认首页或主导航入口。',
    settings_default_home_value: '首页工作台',
    settings_unavailable_section: '当前未开放',
    settings_unavailable_help: '数据刷新频率、通知提醒、图表默认指标等偏好尚未接入当前主线合同，因此这里不再提供可配置入口。',
    settings_save: '保存更改',
    settings_saving: '保存中...',
    settings_reset: '恢复默认',
    settings_load_fallback: '暂时无法读取服务器设置，页面将继续使用本地偏好。',
    settings_saved: '已保存当前可用偏好设置。',
    settings_save_failed: '保存失败，请稍后重试。',
  },
  en: {
    nav_home: 'Home',
    nav_workspace: 'Workspace',
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
    sidebar_watchlist: 'Watchlist',
    sidebar_watchlist_empty: 'No watched stocks yet',
    sidebar_quick_actions: 'Quick Actions',
    sidebar_add_stock: 'Add Stock',
    sidebar_refresh_all: 'Refresh All',
    sidebar_add_watchlist: 'Add to Watchlist',
    sidebar_add_placeholder: 'Enter stock code (e.g. 600519)',
    sidebar_add_submit: 'Add',
    sidebar_cancel: 'Cancel',
    sidebar_watchlist_refreshed: 'Watchlist refreshed',
    sidebar_load_failed: 'Failed to load watchlist',
    sidebar_added_prefix: 'Added',
    sidebar_added_suffix: 'to watchlist',
    sidebar_add_failed: 'Failed to add watchlist item',
    kline_default_title: 'K-Line Chart',
    label_open: 'Open',
    label_high: 'High',
    label_low: 'Low',
    label_close: 'Close',
    label_volume: 'Volume',
    period_1min: '1m',
    period_5min: '5m',
    period_15min: '15m',
    period_day: '1D',
    period_week: '1W',
    period_month: '1M',
    adjust_bfq: 'Raw',
    adjust_qfq: 'Forward',
    adjust_hfq: 'Backward',
    hint_not_available: 'not available yet',
    no_data_prefix: 'No',
    no_data_suffix: 'k-line data',
    no_period_data_suffix: 'data available',
    stock_loading: 'Loading...',
    stock_not_found: 'Stock not found',
    stock_market_sh: 'Shanghai',
    stock_market_sz: 'Shenzhen',
    stock_market_bj: 'Beijing Exchange',
    stock_chart_native: 'Native Chart',
    stock_chart_tv: 'TradingView',
    stock_chart_native_desc: 'Use in-app market data, adjustments, and indicator logic.',
    stock_chart_tv_desc: 'Use TradingView built-in market data and indicators as a complementary view.',
    stock_profile: 'Stock Profile',
    stock_open: 'Open',
    stock_high: 'High',
    stock_low: 'Low',
    stock_turnover: 'Turnover',
    stock_industry: 'Industry',
    stock_list_date: 'List Date',
    stock_actions: 'Quick Actions',
    stock_backtest: 'Backtest',
    stock_watch_add: 'Add to Watchlist',
    stock_watch_remove: 'Remove Watchlist',
    stock_analyze_patterns: 'Analyze Patterns',
    stock_related_patterns: 'Related Patterns',
    stock_no_patterns: 'No pattern data',
    stock_pattern_range_label: 'Evaluation Window',
    stock_pattern_range_current: 'Current chart window',
    stock_pattern_range_focus: 'Evaluation Range',
    stock_pattern_marks_show: 'Show pattern marks',
    stock_pattern_marks_hide: 'Hide pattern marks',
    stock_pattern_focus_range: 'Focus evaluation range',
    stock_pattern_records: 'records',
    stock_pattern_link_hint: 'Hover or focus to sync with the chart',
    stock_tv_pattern_note: 'This list still comes from the in-app pattern engine; TradingView does not render these markers directly.',
    stock_adjust_fallback: 'Adjusted data is unavailable at the moment. Falling back to raw price data.',
    tv_footer_prefix: 'Quotes and built-in indicators are provided by TradingView and remain separate from in-app adjustments and pattern detection.',
    tv_open_full_chart: 'Open full chart',
    tv_no_symbol: 'This symbol is not mapped to TradingView yet, so the advanced chart cannot be displayed.',
    tv_data_level_a_share: 'For A-shares, widget data is mostly end-of-day only, so hourly and minute timeframes are usually unavailable.',
    tv_data_level_bj: 'Coverage for Beijing Exchange symbols in the TradingView widget should be validated ticker by ticker.',
    login_tagline: 'Smart Stock Analysis Platform',
    login_username: 'Username',
    login_username_placeholder: 'Enter your username',
    login_password: 'Password',
    login_password_placeholder: 'Enter your password',
    login_submit: 'Sign In',
    login_submitting: 'Signing in...',
    login_error_default: 'Login failed. Please check your username and password.',
    login_register_prompt: "Don't have an account?",
    login_register_link: 'Create one',
    register_title: 'Create an Account',
    register_email: 'Email',
    register_email_placeholder: 'Enter your email',
    register_submit: 'Register',
    register_submitting: 'Registering...',
    register_cancel: 'Cancel',
    register_success: 'Registration succeeded. Please sign in.',
    register_error_default: 'Registration failed.',
    settings_page_title: 'Settings',
    settings_page_subtitle: 'Only preferences that are already wired up and effective remain available here.',
    settings_current_section: 'Available Now',
    settings_language_label: 'Language',
    settings_language_help: 'Change the interface language and sync it to your account settings.',
    settings_default_home_label: 'Default Home',
    settings_default_home_help: 'The current W3 path keeps the home workbench as the fixed entry. `/workspace` is no longer exposed as the default home or primary navigation target.',
    settings_default_home_value: 'Home Workbench',
    settings_unavailable_section: 'Not Available Yet',
    settings_unavailable_help: 'Refresh cadence, alerts, and default chart indicators are not part of the active W3 contract yet, so they are intentionally not exposed here.',
    settings_save: 'Save Changes',
    settings_saving: 'Saving...',
    settings_reset: 'Restore Default',
    settings_load_fallback: 'Server settings are temporarily unavailable. The page will keep using your local preference.',
    settings_saved: 'Available preferences have been saved.',
    settings_save_failed: 'Save failed. Please try again later.',
  },
}

export const applyLocale = (value: unknown): Locale => {
  const nextLocale = normalizeLocale(value)
  locale.value = nextLocale
  persistLocale(nextLocale)
  syncDocumentLocale(nextLocale)
  return nextLocale
}

export const applyLocaleFromSettings = (settings: { language?: unknown } | null | undefined): Locale => {
  return applyLocale(settings?.language)
}

export function useLocale() {
  const setLocale = (value: Locale) => {
    applyLocale(value)
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
