<template>
  <div v-if="visible && draft" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-shell">
      <aside class="catalog-pane">
        <div class="catalog-search">
          <input v-model.trim="keyword" type="text" placeholder="搜索指标或形态" />
        </div>
        <div class="catalog-groups">
          <button
            v-for="group in filteredGroups"
            :key="group.key"
            class="group-chip"
            :class="{ active: activeGroup === group.key }"
            @click="activeGroup = group.key"
          >
            {{ group.label }}
          </button>
        </div>
        <div class="catalog-list">
          <button
            v-for="metric in activeMetrics"
            :key="metric.key"
            class="metric-row"
            :class="{ active: draft.left.metric_key === metric.key }"
            @click="selectLeftMetric(metric)"
          >
            <strong>{{ metric.label }}</strong>
            <span>{{ metric.description }}</span>
          </button>
        </div>
      </aside>

      <section class="editor-pane">
        <header class="editor-header">
          <div>
            <p class="eyebrow">条件配置</p>
            <h3>{{ draft.label || selectedLeftMetric?.label || '未命名条件' }}</h3>
          </div>
          <button class="close-btn" @click="$emit('close')">关闭</button>
        </header>

        <div class="preview-box">{{ previewText }}</div>

        <div class="form-grid">
          <label>
            <span>条件名</span>
            <input v-model.trim="draft.label" type="text" placeholder="例如：日线 MACD 金叉" />
          </label>

          <label>
            <span>左值输出</span>
            <select v-model="draft.left.output_key">
              <option v-for="output in leftOutputs" :key="output.key" :value="output.key">
                {{ output.label }}
              </option>
            </select>
          </label>
        </div>

        <div v-if="selectedLeftMetric?.params.length" class="param-block">
          <h4>左值参数</h4>
          <div class="form-grid">
            <label v-for="param in selectedLeftMetric.params" :key="param.key">
              <span>{{ param.label }}</span>
              <input
                v-if="param.type !== 'select' && param.type !== 'boolean'"
                v-model.number="draft.left.params[param.key]"
                type="number"
                :min="param.minimum"
                :max="param.maximum"
                :step="param.step ?? 1"
              />
              <select v-else-if="param.type === 'select'" v-model="draft.left.params[param.key]">
                <option v-for="option in param.options || []" :key="String(option.value)" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
              <select v-else v-model="draft.left.params[param.key]">
                <option :value="true">是</option>
                <option :value="false">否</option>
              </select>
            </label>
          </div>
        </div>

        <div class="form-grid">
          <label>
            <span>运算符</span>
            <select v-model="draft.operator">
              <option v-for="operator in supportedOperators" :key="operator.key" :value="operator.key">
                {{ operator.label }}
              </option>
            </select>
          </label>

          <label>
            <span>右值来源</span>
            <select v-model="rightMode">
              <option value="value">常数</option>
              <option value="indicator">另一个指标</option>
            </select>
          </label>
        </div>

        <template v-if="rightMode === 'value'">
          <div class="form-grid single">
            <label>
              <span>常数值</span>
              <select v-if="valueInputKind === 'boolean'" v-model="valueBoolean">
                <option :value="true">是</option>
                <option :value="false">否</option>
              </select>
              <input
                v-else-if="valueInputKind === 'number'"
                v-model.number="valueNumber"
                type="number"
                step="0.1"
              />
              <input v-else v-model="valueText" type="text" />
            </label>
          </div>
        </template>

        <template v-else-if="rightMetric">
          <div class="form-grid">
            <label>
              <span>右值指标</span>
              <select v-model="rightMetricKey" @change="syncRightMetric">
                <option v-for="metric in allMetrics" :key="metric.key" :value="metric.key">
                  {{ metric.label }}
                </option>
              </select>
            </label>

            <label>
              <span>右值输出</span>
              <select v-model="rightMetric.output_key">
                <option v-for="output in rightOutputs" :key="output.key" :value="output.key">
                  {{ output.label }}
                </option>
              </select>
            </label>
          </div>

          <div v-if="selectedRightMetric?.params.length" class="param-block">
            <h4>右值参数</h4>
            <div class="form-grid">
              <label v-for="param in selectedRightMetric.params" :key="param.key">
                <span>{{ param.label }}</span>
                <input
                  v-if="param.type !== 'select' && param.type !== 'boolean'"
                  v-model.number="rightMetric.params[param.key]"
                  type="number"
                  :min="param.minimum"
                  :max="param.maximum"
                  :step="param.step ?? 1"
                />
                <select v-else-if="param.type === 'select'" v-model="rightMetric.params[param.key]">
                  <option v-for="option in param.options || []" :key="String(option.value)" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
                <select v-else v-model="rightMetric.params[param.key]">
                  <option :value="true">是</option>
                  <option :value="false">否</option>
                </select>
              </label>
            </div>
          </div>
        </template>

        <div class="form-grid">
          <label>
            <span>时序规则</span>
            <select v-model="draft.time_rule.mode">
              <option v-for="rule in catalog?.time_rules || []" :key="rule.key" :value="rule.key">
                {{ rule.label }}
              </option>
            </select>
          </label>

          <label>
            <span>回看周期</span>
            <input v-model.number="draft.time_rule.lookback" type="number" min="1" max="240" :disabled="draft.time_rule.mode === 'current'" />
          </label>
        </div>

        <footer class="editor-footer">
          <button class="ghost-btn" @click="$emit('close')">取消</button>
          <button class="primary-btn" @click="submit">确定并刷新</button>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type {
  CatalogGroup,
  CatalogMetric,
  ConditionNode,
  ConstantReference,
  SelectionCatalog,
} from '@/components/selection/types'

const props = defineProps<{
  visible: boolean
  catalog: SelectionCatalog | null
  initialNode: ConditionNode | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', node: ConditionNode): void
}>()

const keyword = ref('')
const activeGroup = ref('technical')
const draft = ref<ConditionNode | null>(null)
const rightMode = ref<'value' | 'indicator'>('value')
const valueNumber = ref<number | null>(0)
const valueText = ref('')
const valueBoolean = ref(true)

const allMetrics = computed(() => props.catalog?.groups.flatMap((group) => group.items) || [])
const metricMap = computed<Record<string, CatalogMetric>>(() => Object.fromEntries(allMetrics.value.map((metric) => [metric.key, metric])))
const operatorMap = computed(() => Object.fromEntries((props.catalog?.operators || []).map((operator) => [operator.key, operator.label])))

const filteredGroups = computed<CatalogGroup[]>(() => {
  const query = keyword.value.toLowerCase()
  if (!query) return props.catalog?.groups || []
  return (props.catalog?.groups || [])
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => `${item.label} ${item.description}`.toLowerCase().includes(query)),
    }))
    .filter((group) => group.items.length > 0)
})

const activeMetrics = computed(() => filteredGroups.value.find((group) => group.key === activeGroup.value)?.items || filteredGroups.value[0]?.items || [])
const selectedLeftMetric = computed(() => (draft.value ? metricMap.value[draft.value.left.metric_key] : undefined))
const leftOutputs = computed(() => selectedLeftMetric.value?.outputs || [])
const supportedOperators = computed(() => {
  const metric = selectedLeftMetric.value
  if (!metric) return props.catalog?.operators || []
  return (props.catalog?.operators || []).filter((operator) => metric.operators.includes(operator.key))
})
const rightMetric = computed(() => (draft.value?.right.source_type === 'indicator' ? draft.value.right : null))
const rightMetricKey = computed({
  get: () => (rightMetric.value ? rightMetric.value.metric_key : allMetrics.value[0]?.key || ''),
  set: (value: string) => {
    if (!draft.value || draft.value.right.source_type !== 'indicator') return
    draft.value.right.metric_key = value
  },
})
const selectedRightMetric = computed(() => (rightMetric.value ? metricMap.value[rightMetric.value.metric_key] : undefined))
const rightOutputs = computed(() => selectedRightMetric.value?.outputs || [])
const valueInputKind = computed(() => {
  const output = leftOutputs.value.find((item) => item.key === draft.value?.left.output_key) || leftOutputs.value[0]
  return output?.kind || 'number'
})

const buildDefaultParams = (metric?: CatalogMetric) => Object.fromEntries((metric?.params || []).map((param) => [param.key, param.default]))
const deepClone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

const syncConstantState = () => {
  if (!draft.value || draft.value.right.source_type !== 'value') return
  const rawValue = draft.value.right.value
  if (typeof rawValue === 'boolean') {
    valueBoolean.value = rawValue
  } else if (typeof rawValue === 'number') {
    valueNumber.value = rawValue
  } else if (rawValue === null || rawValue === undefined) {
    valueNumber.value = 0
  } else {
    valueText.value = String(rawValue)
  }
}

const syncDraftRightValue = () => {
  if (!draft.value || draft.value.right.source_type !== 'value') return
  if (valueInputKind.value === 'boolean') {
    draft.value.right.value = valueBoolean.value
    return
  }
  if (valueInputKind.value === 'number') {
    draft.value.right.value = valueNumber.value
    return
  }
  draft.value.right.value = valueText.value
}

const ensureDraft = () => {
  if (!props.initialNode) {
    draft.value = null
    return
  }
  draft.value = deepClone(props.initialNode)
  rightMode.value = draft.value.right.source_type === 'indicator' ? 'indicator' : 'value'
  activeGroup.value = metricMap.value[draft.value.left.metric_key]?.category || filteredGroups.value[0]?.key || 'technical'
  syncConstantState()
}

const selectLeftMetric = (metric: CatalogMetric) => {
  if (!draft.value) return
  draft.value.left.metric_key = metric.key
  draft.value.left.output_key = metric.default_output
  draft.value.left.params = buildDefaultParams(metric)
  if (!metric.operators.includes(draft.value.operator)) {
    draft.value.operator = metric.operators[0] || 'gt'
  }
  if (rightMode.value === 'indicator') {
    syncRightMetric()
  } else {
    draft.value.right = {
      source_type: 'value',
      value: metric.outputs.find((output) => output.key === metric.default_output)?.kind === 'boolean' ? true : 0,
    }
    syncConstantState()
  }
}

const syncRightMetric = () => {
  if (!draft.value) return
  const metric = metricMap.value[rightMetricKey.value] || allMetrics.value[0]
  if (!metric) return
  draft.value.right = {
    source_type: 'indicator',
    metric_key: metric.key,
    output_key: metric.default_output,
    params: buildDefaultParams(metric),
  }
}

const previewText = computed(() => {
  if (!draft.value) return ''
  const leftMetric = selectedLeftMetric.value
  const left = `${leftMetric?.label || draft.value.left.metric_key}${draft.value.left.output_key ? `.${draft.value.left.output_key}` : ''}`
  const operator = operatorMap.value[draft.value.operator] || draft.value.operator
  const right = draft.value.right.source_type === 'indicator'
    ? `${metricMap.value[draft.value.right.metric_key]?.label || draft.value.right.metric_key}${draft.value.right.output_key ? `.${draft.value.right.output_key}` : ''}`
    : String(draft.value.right.value)
  const timing = draft.value.time_rule.mode === 'current'
    ? '当前周期'
    : draft.value.time_rule.mode === 'all'
      ? `最近 ${draft.value.time_rule.lookback} 个周期连续满足`
      : `最近 ${draft.value.time_rule.lookback} 个周期任意满足`
  return `${left} ${operator} ${right} · ${timing}`
})

const submit = () => {
  if (!draft.value) return
  syncDraftRightValue()
  if (draft.value.time_rule.mode === 'current') {
    draft.value.time_rule.lookback = 1
  }
  emit('save', deepClone(draft.value))
}

watch(() => props.visible, (visible) => {
  if (visible) {
    ensureDraft()
  } else {
    keyword.value = ''
  }
}, { immediate: true })

watch(metricMap, () => {
  if (props.visible) ensureDraft()
})

watch(rightMode, (mode) => {
  if (!draft.value) return
  if (mode === 'indicator') {
    syncRightMetric()
  } else {
    draft.value.right = {
      source_type: 'value',
      value: valueInputKind.value === 'boolean' ? true : 0,
    } as ConstantReference
    syncConstantState()
  }
})

watch(valueNumber, syncDraftRightValue)
watch(valueText, syncDraftRightValue)
watch(valueBoolean, syncDraftRightValue)
</script>

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(4, 6, 9, 0.72);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 2000;
}

.modal-shell {
  width: min(1200px, 100%);
  max-height: min(90vh, 920px);
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  overflow: hidden;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(16, 19, 23, 0.98), rgba(8, 10, 13, 0.98));
}

.catalog-pane,
.editor-pane {
  padding: 24px;
  overflow-y: auto;
}

.catalog-pane {
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.catalog-search input,
.editor-pane input,
.editor-pane select {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  padding: 11px 12px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.92);
}

.catalog-groups {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0;
}

.group-chip,
.metric-row,
.close-btn,
.ghost-btn,
.primary-btn {
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.9);
  cursor: pointer;
}

.group-chip {
  border-radius: 999px;
  padding: 8px 12px;
}

.group-chip.active {
  background: rgba(84, 172, 255, 0.18);
  border-color: rgba(84, 172, 255, 0.4);
}

.catalog-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-row {
  text-align: left;
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-row.active {
  border-color: rgba(84, 172, 255, 0.45);
  background: rgba(84, 172, 255, 0.12);
}

.metric-row span {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.58);
}

.editor-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0 0 6px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.4);
}

.editor-header h3,
.param-block h4 {
  margin: 0;
  color: rgba(255, 255, 255, 0.94);
}

.preview-box {
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.5;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.form-grid.single {
  grid-template-columns: minmax(0, 1fr);
}

label {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

label span {
  color: rgba(255, 255, 255, 0.62);
  font-size: 13px;
}

.param-block {
  margin-bottom: 18px;
  padding: 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.editor-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
}

.close-btn,
.ghost-btn,
.primary-btn {
  border-radius: 999px;
  padding: 10px 16px;
}

.primary-btn {
  background: linear-gradient(135deg, #4b9cff, #7bc8ff);
  color: #081018;
  border-color: transparent;
}

@media (max-width: 980px) {
  .modal-shell {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
