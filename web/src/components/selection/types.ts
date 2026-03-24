export interface CatalogOption {
  value: string | number | boolean
  label: string
}

export interface CatalogParam {
  key: string
  label: string
  type: 'number' | 'text' | 'select' | 'boolean'
  default: string | number | boolean | null
  minimum?: number
  maximum?: number
  step?: number
  options?: CatalogOption[]
}

export interface CatalogOutput {
  key: string
  label: string
  kind: 'number' | 'boolean'
}

export interface CatalogMetric {
  key: string
  label: string
  category: string
  description: string
  outputs: CatalogOutput[]
  operators: string[]
  params: CatalogParam[]
  default_output: string
  right_operand_modes: Array<'value' | 'indicator'>
}

export interface CatalogGroup {
  key: string
  label: string
  items: CatalogMetric[]
}

export interface SelectionCatalog {
  version: number
  periods: Array<{ key: 'daily' | 'weekly' | 'monthly'; label: string }>
  operators: Array<{ key: string; label: string }>
  time_rules: Array<{ key: 'current' | 'any' | 'all'; label: string }>
  groups: CatalogGroup[]
}

export interface MetricReference {
  source_type: 'indicator'
  metric_key: string
  output_key?: string
  params: Record<string, string | number | boolean | null>
}

export interface ConstantReference {
  source_type: 'value'
  value: string | number | boolean | null
}

export type OperandReference = MetricReference | ConstantReference

export interface TimeRule {
  mode: 'current' | 'any' | 'all'
  lookback: number
}

export interface ConditionNode {
  node_type: 'condition'
  id: string
  label?: string
  left: MetricReference
  operator: string
  right: OperandReference
  time_rule: TimeRule
  weight: number
}

export interface GroupNode {
  node_type: 'group'
  id: string
  label?: string
  combinator: 'and' | 'or' | 'not'
  children: SelectionNode[]
}

export type SelectionNode = ConditionNode | GroupNode

export interface SelectionPreset {
  id: number
  user_id: number
  name: string
  category: string
  description?: string | null
  params?: {
    version?: number
    name?: string
    period?: 'daily' | 'weekly' | 'monthly'
    root?: GroupNode
  } | null
  is_active: boolean
}

export interface SelectionResultItem {
  selection_id?: string | null
  ts_code: string
  code: string
  stock_name: string
  trade_date: string
  date: string
  score: number
  signal: string
  matched_conditions?: number
  total_conditions?: number
  snapshot?: {
    close?: number | null
    pct_chg?: number | null
    volume?: number | null
    amount?: number | null
  }
  explanations?: Array<{
    id: string
    label: string
    metric_key: string
    output_key: string
    operator: string
    matched: boolean
    score: number
    latest_left: string | number | boolean | null
    latest_right: string | number | boolean | null
    match_left: string | number | boolean | null
    match_right: string | number | boolean | null
    match_count: number
    last_match_date?: string | null
  }>
}

export interface SelectionRunResponse {
  selection_id?: string | null
  trade_date?: string | null
  period: 'daily' | 'weekly' | 'monthly'
  matched_count: number
  items: SelectionResultItem[]
}
