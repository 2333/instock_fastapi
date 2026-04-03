<template>
  <div class="alerts-page">
    <div class="page-header">
      <h1>预警管理</h1>
      <p class="subtitle">设置股价与指标预警，及时掌握市场变化</p>
      <button class="btn btn-primary" @click="openCreateModal">+ 新建预警</button>
    </div>

    <div class="alerts-content">
      <div class="alerts-list">
        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else-if="alerts.length === 0" class="empty-state">
          <p>暂无预警条件</p>
          <button class="btn btn-secondary" @click="openCreateModal">创建第一个预警</button>
        </div>
        <div v-else class="list-items">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="alert-item"
            :class="{ disabled: !alert.is_active }"
          >
            <div class="alert-main">
              <div class="alert-header">
                <span class="alert-name">{{ alert.name }}</span>
                <span class="alert-code">{{ alert.code }}</span>
                <span class="status-badge" :class="alert.is_active ? 'active' : 'inactive'">
                  {{ alert.is_active ? '启用' : '已禁用' }}
                </span>
              </div>
              <div class="alert-condition">
                <span class="condition-type">{{ getConditionLabel(alert.condition) }}</span>
                <span class="condition-op">{{ getOperatorLabel(alert.condition.operator) }}</span>
                <span class="condition-value">{{ alert.condition.value }}</span>
              </div>
              <div v-if="alert.last_triggered_at" class="alert-meta">
                最后触发：{{ formatDate(alert.last_triggered_at) }}
              </div>
            </div>
            <div class="alert-actions">
              <button class="btn-icon" @click="openEditModal(alert)" title="编辑">
                ✏️
              </button>
              <button
                class="btn-icon"
                @click="toggleActive(alert)"
                :title="alert.is_active ? '禁用' : '启用'"
              >
                {{ alert.is_active ? '⏸️' : '▶️' }}
              </button>
              <button class="btn-icon danger" @click="openDeleteConfirm(alert)" title="删除">
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑模态框 -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ editingAlert ? '编辑预警' : '新建预警' }}</h2>
          <button class="btn-close" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveAlert">
            <div class="form-group">
              <label>预警名称</label>
              <input v-model="formData.name" type="text" placeholder="例如：茅台突破 1800 元" required />
            </div>
            <div class="form-group">
              <label>股票代码</label>
              <input v-model="formData.code" type="text" placeholder="600519" required />
            </div>
            <div class="form-group">
              <label>条件类型</label>
              <select v-model="formData.condition.type" @change="resetConditionValue">
                <option value="price">价格</option>
                <option value="rsi">RSI 指标</option>
                <option value="change">涨跌幅</option>
              </select>
            </div>
            <div class="form-group">
              <label>比较运算符</label>
              <select v-model="formData.condition.operator">
                <option value="gt">大于 (>)</option>
                <option value="gte">大于等于 (≥)</option>
                <option value="lt">小于 (<)</option>
                <option value="lte">小于等于 (≤)</option>
              </select>
            </div>
            <div class="form-group">
              <label>阈值</label>
              <input v-model.number="formData.condition.value" type="number" step="0.01" required />
            </div>
            <div class="form-group">
              <label>通知渠道</label>
              <div class="checkbox-group">
                <label><input type="checkbox" v-model="formData.notify_channels" value="in_app" /> 应用内通知</label>
                <label><input type="checkbox" v-model="formData.notify_channels" value="email" /> 邮件（待接入）</label>
              </div>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click="closeModal">取消</button>
              <button type="submit" class="btn btn-primary" :disabled="saving">
                {{ saving ? '保存中...' : '保存' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { alertApi } from '@/api'

const alerts = ref<any[]>([])
const loading = ref(false)
const showModal = ref(false)
const editingAlert = ref<any | null>(null)
const saving = ref(false)

const formData = ref({
  name: '',
  code: '',
  condition: {
    type: 'price',
    operator: 'gt',
    value: 0,
  },
  notify_channels: ['in_app'],
})

onMounted(async () => {
  await fetchAlerts()
})

async function fetchAlerts() {
  loading.value = true
  try {
    const res = await alertApi.list()
    alerts.value = res.data || []
  } catch (e) {
    console.error('Failed to fetch alerts:', e)
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  editingAlert.value = null
  resetForm()
  showModal.value = true
}

function openEditModal(alert: any) {
  editingAlert.value = alert
  formData.value = {
    name: alert.name,
    code: alert.code,
    condition: { ...alert.condition },
    notify_channels: [...(alert.notify_channels || ['in_app'])],
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingAlert.value = null
}

function resetForm() {
  formData.value = {
    name: '',
    code: '',
    condition: { type: 'price', operator: 'gt', value: 0 },
    notify_channels: ['in_app'],
  }
}

function resetConditionValue() {
  formData.value.condition.value = getDefaultValue(formData.value.condition.type)
}

function getDefaultValue(type: string): number {
  switch (type) {
    case 'price': return 10
    case 'rsi': return 30
    case 'change': return 5
    default: return 0
  }
}

function getConditionLabel(condition: any): string {
  const labels: Record<string, string> = {
    price: '价格',
    rsi: 'RSI',
    change: '涨跌幅',
  }
  return labels[condition.type] || condition.type
}

function getOperatorLabel(op: string): string {
  const labels: Record<string, string> = {
    gt: '大于',
    gte: '大于等于',
    lt: '小于',
    lte: '小于等于',
  }
  return labels[op] || op
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function saveAlert() {
  saving.value = true
  try {
    if (editingAlert.value) {
      await alertApi.update(editingAlert.value.id, formData.value)
    } else {
      await alertApi.create(formData.value)
    }
    closeModal()
    await fetchAlerts()
  } catch (e) {
    console.error('Failed to save alert:', e)
    alert('保存失败')
  } finally {
    saving.value = false
  }
}

async function toggleActive(alert: any) {
  try {
    await alertApi.update(alert.id, { is_active: !alert.is_active })
    alert.is_active = !alert.is_active
  } catch (e) {
    console.error('Failed to toggle alert:', e)
  }
}

async function openDeleteConfirm(alert: any) {
  if (!confirm(`确定删除预警"${alert.name}"？`)) return
  try {
    await alertApi.remove(alert.id)
    alerts.value = alerts.value.filter(a => a.id !== alert.id)
  } catch (e) {
    console.error('Failed to delete alert:', e)
    alert('删除失败')
  }
}
</script>

<style scoped lang="scss">
.alerts-page {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;

  h1 {
    margin: 0;
    font-size: 24px;
  }

  .subtitle {
    color: var(--color-text-secondary);
    margin: 4px 0 0;
  }
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 0;
  color: var(--color-text-secondary);
}

.list-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-item {
  background: var(--color-bg-secondary);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-left: 4px solid var(--color-primary);

  &.disabled {
    opacity: 0.6;
    border-left-color: var(--color-text-tertiary);
  }
}

.alert-main {
  flex: 1;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;

  .alert-name {
    font-weight: 600;
    font-size: 16px;
  }

  .alert-code {
    font-family: monospace;
    background: var(--color-bg-tertiary);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
  }

  .status-badge {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;

    &.active {
      background: var(--color-success-light);
      color: var(--color-success);
    }
    &.inactive {
      background: var(--color-text-tertiary);
      color: var(--color-text-secondary);
    }
  }
}

.alert-condition {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;

  .condition-type {
    font-weight: 500;
  }

  .condition-op {
    color: var(--color-text-secondary);
  }

  .condition-value {
    font-family: monospace;
    color: var(--color-primary);
    font-weight: 600;
  }
}

.alert-meta {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.alert-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s;

  &:hover {
    background: var(--color-bg-tertiary);
  }

  &.danger:hover {
    background: var(--color-error-light);
  }
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--color-bg-primary);
  border-radius: 8px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);

  h2 {
    margin: 0;
    font-size: 18px;
  }

  .btn-close {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--color-text-secondary);
  }
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;

  label {
    display: block;
    margin-bottom: 6px;
    font-weight: 500;
    font-size: 14px;
  }

  input[type="text"],
  input[type="number"],
  select {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    font-size: 14px;
    background: var(--color-bg-primary);

    &:focus {
      outline: none;
      border-color: var(--color-primary);
      box-shadow: 0 0 0 2px var(--color-primary-light);
    }
  }
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;

  label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: normal;
    cursor: pointer;
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}
</style>
