/**
 * 统一字段规范化层
 * 将后端返回的各种字段格式统一为前端使用的格式
 */

// 后端原始字段类型
export interface RawStockData {
  date?: string
  code?: string
  name?: string | null
  new_price?: number | null
  change_rate?: number | null
  ups_downs?: number | null
  volume?: number | null
  deal_amount?: number | null
  turnoverrate?: number | null
  open?: number | null
  high?: number | null
  low?: number | null
  close?: number | null
  pre_close?: number | null
  vol?: number | null
  amount?: number | null
  ts_code?: string | null
  symbol?: string | null
  // 原始字段可能是其他名称
  [key: string]: unknown
}

// 统一后的字段类型
export interface NormalizedStock {
  code: string           // 股票代码 (600000)
  name: string           // 股票名称
  price: number          // 最新价格
  change: number         // 涨跌额
  changeRate: number     // 涨跌幅 (%)
  volume: number         // 成交量
  amount: number         //成交额
  turnoverRate: number   // 换手率 (%)
  open: number           // 开盘价
  high: number          // 最高价
  low: number           // 最低价
  close: number          // 收盘价
  preClose: number       // 昨收价
}

// 指数数据
export interface NormalizedIndex {
  code: string           // 指数代码 (sh000001)
  name: string          // 指数名称
  current: number        // 当前点位
  change: number         // 涨跌点数
  changeRate: number     // 涨跌幅 (%)
  volume: number         // 成交量
  amount: number         // 成交额
  high?: number | null   // 最高
  low?: number | null    // 最低
  open?: number | null   // 开盘
}

// 字段映射配置
const FIELD_MAPPING = {
  // 价格字段
  price: ['new_price', 'close', 'price', 'current'],
  open: ['open', 'open_price'],
  high: ['high', 'high_price'],
  low: ['low', 'low_price'],
  close: ['close', 'new_price'],
  preClose: ['pre_close', 'pre_close_price', 'previous_close'],
  
  // 涨跌字段
  change: ['ups_downs', 'change', 'change_amount', 'diff'],
  changeRate: ['change_rate', 'change_pct', 'pct_change', 'chg'],
  
  // 量价字段
  volume: ['volume', 'vol', 'volumn', 'trade_vol'],
  amount: ['amount', 'deal_amount', 'turnover', 'trade_amount'],
  
  // 换手率
  turnoverRate: ['turnoverrate', 'turnover_rate', 'turnover_rate_pct'],
}

/**
 * 获取第一个非空值
 */
function getFirstValue<T>(data: RawStockData, fields: string[]): T | null {
  for (const field of fields) {
    const value = data[field]
    if (value !== null && value !== undefined && value !== '') {
      return value as T
    }
  }
  return null
}

function normalizeDisplayCode(value: string | null | undefined): string {
  if (!value) return ''
  return String(value).split('.')[0]
}

/**
 * 标准化股票数据
 */
export function normalizeStock(data: RawStockData): NormalizedStock {
  const price = getFirstValue<number>(data, FIELD_MAPPING.price) ?? 0
  const preClose = getFirstValue<number>(data, FIELD_MAPPING.preClose) ?? price
  const change = getFirstValue<number>(data, FIELD_MAPPING.change) ?? 0
  
  // changeRate 可能是小数 (0.03) 或百分比 (3.0)，需要判断
  let changeRate = getFirstValue<number>(data, FIELD_MAPPING.changeRate) ?? 0
  // 如果 changeRate 绝对值 <= 1，认为是小数形式，转换为百分比
  if (Math.abs(changeRate) <= 1 && changeRate !== 0) {
    changeRate = changeRate * 100
  }

  return {
    code: normalizeDisplayCode(getFirstValue<string>(data, ['code', 'ts_code', 'symbol'])),
    name: getFirstValue<string>(data, ['name']) ?? '-',
    price,
    change,
    changeRate,
    volume: getFirstValue<number>(data, FIELD_MAPPING.volume) ?? 0,
    amount: getFirstValue<number>(data, FIELD_MAPPING.amount) ?? 0,
    turnoverRate: getFirstValue<number>(data, FIELD_MAPPING.turnoverRate) ?? 0,
    open: getFirstValue<number>(data, FIELD_MAPPING.open) ?? 0,
    high: getFirstValue<number>(data, FIELD_MAPPING.high) ?? 0,
    low: getFirstValue<number>(data, FIELD_MAPPING.low) ?? 0,
    close: getFirstValue<number>(data, FIELD_MAPPING.close) ?? price,
    preClose,
  }
}

/**
 * 标准化指数数据
 */
export function normalizeIndex(data: RawStockData): NormalizedIndex {
  const current = getFirstValue<number>(data, FIELD_MAPPING.price) ?? 0
  
  // 指数的 change 字段处理
  let change = getFirstValue<number>(data, FIELD_MAPPING.change) ?? 0
  let changeRate = getFirstValue<number>(data, FIELD_MAPPING.changeRate) ?? 0
  
  // 如果 changeRate 绝对值 <= 1，转换为百分比
  if (Math.abs(changeRate) <= 1 && changeRate !== 0) {
    changeRate = changeRate * 100
  }

  return {
    code: normalizeDisplayCode(getFirstValue<string>(data, ['code', 'ts_code'])),
    name: getFirstValue<string>(data, ['name']) ?? '-',
    current,
    change,
    changeRate,
    volume: getFirstValue<number>(data, FIELD_MAPPING.volume) ?? 0,
    amount: getFirstValue<number>(data, FIELD_MAPPING.amount) ?? 0,
    high: getFirstValue<number>(data, FIELD_MAPPING.high),
    low: getFirstValue<number>(data, FIELD_MAPPING.low),
    open: getFirstValue<number>(data, FIELD_MAPPING.open),
  }
}

/**
 * 批量标准化股票数据
 */
export function normalizeStockList(data: RawStockData[]): NormalizedStock[] {
  return data.map(normalizeStock)
}

/**
 * 格式化涨跌幅显示
 */
export function formatChangeRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  const prefix = value >= 0 ? '+' : ''
  return `${prefix}${value.toFixed(2)}%`
}

/**
 * 格式化价格
 */
export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2)
}

/**
 * 格式化成交量
 */
export function formatVolume(value: number | null | undefined): string {
  if (!value) return '-'
  if (value >= 100000000) return (value / 100000000).toFixed(2) + '亿'
  if (value >= 10000) return (value / 10000).toFixed(2) + '万'
  return value.toString()
}

/**
 * 格式化成交额
 */
export function formatAmount(value: number | null | undefined): string {
  if (!value) return '-'
  if (value >= 1000000000) return (value / 1000000000).toFixed(2) + 'B'
  if (value >= 1000000) return (value / 1000000).toFixed(2) + 'M'
  if (value >= 1000) return (value / 1000).toFixed(2) + 'K'
  return value.toString()
}

/**
 * 指数代码映射
 * A股常见指数代码
 */
export const INDEX_CODES = {
  // 上证
  SHANGHAI_COMPOSITE: 'sh000001',   // 上证综指
  SHANGHAI_50: 'sh000016',           // 上证50
  SHANGHAI_300: 'sh000300',          // 沪深300
  STAR_50: 'sh000688',               // 科创50
  
  // 深证
  SHENZHEN_COMPONENT: 'sz399001',    // 深证成指
  SHENZHEN_100: 'sz399010',          // 深证100
  CHINEXT: 'sz399006',               // 创业板指
  CHINEXT_100: 'sz399012',           // 创业板100
  
  // 其他
  CSI_300: 'sh000300',               // 沪深300
  CSI_500: 'sh000905',               // 中证500
} as const

/**
 * 根据代码获取指数名称
 */
export function getIndexName(code: string): string {
  const names: Record<string, string> = {
    'sh000001': '上证指数',
    'sh000016': '上证50',
    'sh000300': '沪深300',
    'sh000688': '科创50',
    'sz399001': '深证成指',
    'sz399010': '深证100',
    'sz399006': '创业板指',
    'sz399012': '创业板100',
    'sh000905': '中证500',
  }
  return names[code] || code
}

/**
 * 判断是否为指数代码
 */
export function isIndexCode(code: string): boolean {
  return code.startsWith('sh000') || code.startsWith('sz399')
}
