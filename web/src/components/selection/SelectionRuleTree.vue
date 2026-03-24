<template>
  <section class="group-card" :style="{ '--depth': String(depth) }">
    <header class="group-header">
      <div>
        <p class="group-meta">{{ depth === 0 ? '根规则组' : '子规则组' }}</p>
        <div class="group-title-row">
          <h3>{{ node.label || `规则组 ${node.id.slice(-4)}` }}</h3>
          <select class="group-select" :value="node.combinator" @change="onCombinatorChange">
            <option value="and">AND</option>
            <option value="or">OR</option>
            <option value="not">NOT</option>
          </select>
        </div>
      </div>
      <div class="group-actions">
        <button class="ghost-btn" @click="$emit('add-condition', node.id)">添加条件</button>
        <button class="ghost-btn" @click="$emit('add-group', node.id)">添加子组</button>
        <button v-if="depth > 0" class="danger-btn" @click="$emit('remove-node', node.id)">删除组</button>
      </div>
    </header>

    <div class="group-children">
      <div v-if="!node.children.length" class="group-empty">
        这个组还没有条件。先加一个指标条件，或再拆一个子组。
      </div>

      <template v-for="child in node.children" :key="child.id">
        <SelectionRuleTree
          v-if="child.node_type === 'group'"
          :node="child"
          :depth="depth + 1"
          :metric-map="metricMap"
          :operator-labels="operatorLabels"
          @add-condition="$emit('add-condition', $event)"
          @add-group="$emit('add-group', $event)"
          @edit-condition="$emit('edit-condition', $event)"
          @remove-node="$emit('remove-node', $event)"
          @update-group="$emit('update-group', $event)"
        />

        <article v-else class="condition-card">
          <div class="condition-main">
            <p class="condition-pill">条件</p>
            <h4>{{ child.label || metricLabel(child.left.metric_key) }}</h4>
            <p class="condition-summary">{{ renderCondition(child) }}</p>
          </div>
          <div class="condition-actions">
            <button class="ghost-btn" @click="$emit('edit-condition', child.id)">配置</button>
            <button class="danger-btn" @click="$emit('remove-node', child.id)">删除</button>
          </div>
        </article>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CatalogMetric, ConditionNode, GroupNode } from '@/components/selection/types'

defineOptions({ name: 'SelectionRuleTree' })

const props = defineProps<{
  node: GroupNode
  depth: number
  metricMap: Record<string, CatalogMetric>
  operatorLabels: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'add-condition', groupId: string): void
  (e: 'add-group', groupId: string): void
  (e: 'edit-condition', nodeId: string): void
  (e: 'remove-node', nodeId: string): void
  (e: 'update-group', payload: { id: string; combinator: 'and' | 'or' | 'not' }): void
}>()

const operatorLabels = computed(() => props.operatorLabels)

const metricLabel = (key: string) => props.metricMap[key]?.label || key

const formatParams = (params: Record<string, unknown>) => {
  const entries = Object.entries(params || {}).filter(([, value]) => value !== null && value !== '' && value !== undefined)
  if (!entries.length) return ''
  return `(${entries.map(([key, value]) => `${key}=${value}`).join(', ')})`
}

const renderOperand = (operand: ConditionNode['right']) => {
  if (operand.source_type === 'value') {
    return String(operand.value)
  }
  return `${metricLabel(operand.metric_key)}${operand.output_key ? `.${operand.output_key}` : ''}${formatParams(operand.params)}`
}

const renderTimeRule = (condition: ConditionNode) => {
  if (condition.time_rule.mode === 'current') return '当前周期'
  if (condition.time_rule.mode === 'all') return `最近 ${condition.time_rule.lookback} 个周期连续满足`
  return `最近 ${condition.time_rule.lookback} 个周期任意满足`
}

const renderCondition = (condition: ConditionNode) => {
  const left = `${metricLabel(condition.left.metric_key)}${condition.left.output_key ? `.${condition.left.output_key}` : ''}${formatParams(condition.left.params)}`
  const operator = operatorLabels.value[condition.operator] || condition.operator
  return `${left} ${operator} ${renderOperand(condition.right)} · ${renderTimeRule(condition)}`
}

const onCombinatorChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  emit('update-group', { id: props.node.id, combinator: target.value as 'and' | 'or' | 'not' })
}
</script>

<style scoped lang="scss">
.group-card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(17, 20, 24, 0.92), rgba(10, 12, 15, 0.96));
  padding: 18px;
  position: relative;
}

.group-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 18px;
  pointer-events: none;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.group-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.group-meta {
  margin: 0 0 6px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.42);
}

.group-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.group-title-row h3 {
  margin: 0;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.92);
}

.group-select {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.88);
  padding: 6px 12px;
}

.group-actions,
.condition-actions {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.group-children {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.group-empty {
  border: 1px dashed rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  padding: 18px;
  color: rgba(255, 255, 255, 0.56);
}

.condition-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  border-radius: 14px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.condition-main h4 {
  margin: 0 0 6px;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
}

.condition-pill {
  margin: 0 0 6px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #86b7ff;
}

.condition-summary {
  margin: 0;
  color: rgba(255, 255, 255, 0.68);
  line-height: 1.5;
}

.ghost-btn,
.danger-btn {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.88);
  cursor: pointer;
}

.danger-btn {
  color: #ffb4b4;
}

@media (max-width: 900px) {
  .group-header,
  .condition-card {
    flex-direction: column;
  }
}
</style>
