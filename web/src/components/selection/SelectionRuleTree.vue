<template>
  <section :class="['condition-group', { root: depth === 0 }]">
    <header class="group-toolbar">
      <div class="group-heading">
        <span class="group-tag">{{ depth === 0 ? '主条件组' : '子条件组' }}</span>
        <h3>{{ depth === 0 ? '全部条件' : (node.label || `条件组 ${node.id.slice(-4)}`) }}</h3>
      </div>
      <div class="group-controls">
        <select class="group-select" :value="node.combinator" @change="onCombinatorChange">
          <option value="and">AND</option>
          <option value="or">OR</option>
          <option value="not">NOT</option>
        </select>
        <button class="btn btn-secondary" @click="$emit('add-condition', node.id)">添加条件</button>
        <button class="btn btn-secondary" @click="$emit('add-group', node.id)">添加子组</button>
        <button v-if="depth > 0" class="btn btn-danger" @click="$emit('remove-node', node.id)">删除分组</button>
      </div>
    </header>

    <div class="group-children">
      <div v-if="!node.children.length" class="group-empty">
        当前还没有条件。先添加一个条件，或者拆出一个子组来组合逻辑。
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

        <article v-else class="condition-item">
          <div class="condition-body">
            <div class="condition-header">
              <h4>{{ child.label || metricLabel(child.left.metric_key) }}</h4>
              <span class="condition-tag">条件</span>
            </div>
            <p class="condition-summary">{{ renderCondition(child) }}</p>
          </div>
          <div class="condition-actions">
            <button class="btn btn-secondary" @click="$emit('edit-condition', child.id)">编辑</button>
            <button class="btn btn-danger" @click="$emit('remove-node', child.id)">删除</button>
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
.condition-group {
  border-left: 2px solid rgba(41, 98, 255, 0.2);
  padding-left: 16px;

  &.root {
    border-left: none;
    padding-left: 0;
  }
}

.condition-group:not(.root) {
  margin-left: 6px;
  padding-top: 4px;
}

.group-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.group-heading {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.group-tag {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.42);
}

.group-heading h3 {
  margin: 0;
  font-size: 17px;
  color: rgba(255, 255, 255, 0.92);
}

.group-controls,
.condition-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.group-select {
  min-width: 88px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.88);
}

.group-children {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-empty {
  border: 1px dashed rgba(255, 255, 255, 0.14);
  border-radius: 12px;
  padding: 16px;
  color: rgba(255, 255, 255, 0.54);
  font-size: 13px;
}

.condition-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.condition-body {
  min-width: 0;
}

.condition-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.condition-header h4 {
  margin: 0;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.92);
}

.condition-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(41, 98, 255, 0.14);
  color: #8fb7ff;
  font-size: 11px;
  font-weight: 600;
}

.condition-summary {
  margin: 0;
  color: rgba(255, 255, 255, 0.64);
  line-height: 1.5;
  font-size: 13px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:hover {
  border-color: rgba(41, 98, 255, 0.3);
  background: rgba(41, 98, 255, 0.08);
}

.btn-danger {
  color: #ffb5b5;
}

.btn-danger:hover {
  border-color: rgba(255, 23, 68, 0.28);
  background: rgba(255, 23, 68, 0.08);
}

@media (max-width: 900px) {
  .group-toolbar,
  .condition-item {
    flex-direction: column;
  }
}
</style>
