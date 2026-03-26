import type { Locale } from '@/composables/useLocale'

const PATTERN_LABELS: Record<string, Record<Locale, string>> = {
  MORNING_STAR: { zh: '晨星', en: 'Morning Star' },
  EVENING_STAR: { zh: '夜星', en: 'Evening Star' },
  BREAKTHROUGH_HIGH: { zh: '突破高点', en: 'Breakout High' },
  BREAKDOWN_LOW: { zh: '跌破低点', en: 'Breakdown Low' },
  CONTINUOUS_RISE: { zh: '连续上涨', en: 'Consecutive Rise' },
  CONTINUOUS_FALL: { zh: '连续下跌', en: 'Consecutive Fall' },
  BULLISH_ENGULFING: { zh: '看涨吞没', en: 'Bullish Engulfing' },
  BEARISH_ENGULFING: { zh: '看跌吞没', en: 'Bearish Engulfing' },
  BULLISH_HARAMI: { zh: '看涨孕线', en: 'Bullish Harami' },
  BEARISH_HARAMI: { zh: '看跌孕线', en: 'Bearish Harami' },
  HAMMER: { zh: '锤子线', en: 'Hammer' },
  INVERTED_HAMMER: { zh: '倒锤子', en: 'Inverted Hammer' },
  DOJI: { zh: '十字星', en: 'Doji' },
  SPINNING_TOP: { zh: '纺锤线', en: 'Spinning Top' },
  MARUBOZU: { zh: '光头光脚', en: 'Marubozu' },
  SHOOTING_STAR: { zh: '射击之星', en: 'Shooting Star' },
  PIERCING: { zh: '穿刺', en: 'Piercing Pattern' },
  DARK_CLOUD_COVER: { zh: '乌云盖顶', en: 'Dark Cloud Cover' },
  HANGING_MAN: { zh: '吊人', en: 'Hanging Man' },
  DRAGONFLY_DOJI: { zh: '龙爪', en: 'Dragonfly Doji' },
  GRAVESTONE_DOJI: { zh: '墓碑', en: 'Gravestone Doji' },
  TRISTAR: { zh: '三星', en: 'Tri-Star' },
  TAKURI: { zh: '探水杆', en: 'Takuri' },
  THREE_WHITE_SOLDIERS: { zh: '红三兵', en: 'Three White Soldiers' },
  THREE_BLACK_CROWS: { zh: '黑三鸦', en: 'Three Black Crows' },
  MA_GOLDEN_CROSS: { zh: 'MA金叉', en: 'MA Golden Cross' },
  MA_DEATH_CROSS: { zh: 'MA死叉', en: 'MA Death Cross' },
}

export const getPatternLabel = (name: string, locale: Locale) => {
  return PATTERN_LABELS[name]?.[locale] || name
}
