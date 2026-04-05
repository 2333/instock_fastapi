<template>
  <div class="preferences-page">
    <div class="page-header">
      <div class="header-left">
        <button class="btn btn-secondary btn-small" @click="goBack">← 返回</button>
        <h1>报告偏好设置</h1>
      </div>
      <div class="header-right">
        <button class="btn btn-primary" @click="savePreferences" :disabled="saving">
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else class="preferences-form">
      <div class="form-section">
        <h3>报告类型</h3>
        <p class="section-desc">选择您希望接收的报告类型</p>

        <div class="toggle-group">
          <label class="toggle-item">
            <span class="toggle-label">
              每日报告
              <span class="toggle-hint">每天收盘后生成</span>
            </span>
            <input
              type="checkbox"
              v-model="preferences.daily_enabled"
              class="toggle-input"
            >
            <span class="toggle-slider"></span>
          </label>

          <label class="toggle-item">
            <span class="toggle-label">
              每周报告
              <span class="toggle-hint">每周五收盘后生成</span>
            </span>
            <input
              type="checkbox"
              v-model="preferences.weekly_enabled"
              class="toggle-input"
            >
            <span class="toggle-slider"></span>
          </label>

          <label class="toggle-item">
            <span class="toggle-label">
              每月报告
              <span class="toggle-hint">每月最后一个交易日收盘后生成</span>
            </span>
            <input
              type="checkbox"
              v-model="preferences.monthly_enabled"
              class="toggle-input"
            >
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div class="form-section">
        <h3>接收邮箱</h3>
        <p class="section-desc">报告生成后将发送至您的邮箱</p>

        <div class="form-item">
          <label>邮箱地址</label>
          <input
            type="email"
            v-model="preferences.email"
            placeholder="your@email.com"
            class="input-full"
          >
        </div>
      </div>

      <div class="form-section">
        <h3>包含指标</h3>
        <p class="section-desc">选择报告中希望展示的指标</p>

        <div class="checkbox-group">
          <label v-for="metric in availableMetrics" :key="metric.key" class="checkbox-item">
            <input
              type="checkbox"
              :value="metric.key"
              v-model="preferences.metrics"
            >
            <span class="checkbox-label">{{ metric.label }}</span>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalytics } from '@/composables/useAnalytics'
import { reportApi } from '@/api'

const router = useRouter()
const { pageView } = useAnalytics()

// 状态
const loading = ref(false)
const saving = ref(false)

// 偏好设置
const preferences = reactive({
  daily_enabled: true,
  weekly_enabled: true,
  monthly_enabled: false,
  email: '',
  metrics: ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate'],
})

const availableMetrics = [
  { key: 'total_return', label: '总收益率' },
  { key: 'annualized_return', label: '年化收益率' },
  { key: 'sharpe_ratio', label: '夏普比率' },
  { key: 'max_drawdown', label: '最大回撤' },
  { key: 'win_rate', label: '胜率' },
  { key: 'total_trades', label: '交易次数' },
  { key: 'profit_factor', label: '盈亏比' },
  { key: 'avg_win', label: '平均盈利' },
  { key: 'avg_loss', label: '平均亏损' },
]

async function loadPreferences() {
  loading.value = true
  try {
    const res = await reportApi.getPreferences()
    const data = res.data
    if (data) {
      preferences.daily_enabled = data.daily_enabled ?? true
      preferences.weekly_enabled = data.weekly_enabled ?? true
      preferences.monthly_enabled = data.monthly_enabled ?? false
      preferences.email = data.email || ''
      preferences.metrics = data.metrics || ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
    }
  } catch (error) {
    console.error('Failed to load preferences:', error)
  } finally {
    loading.value = false
  }
}

async function savePreferences() {
  saving.value = true
  try {
    await reportApi.updatePreferences({
      daily_enabled: preferences.daily_enabled,
      weekly_enabled: preferences.weekly_enabled,
      monthly_enabled: preferences.monthly_enabled,
      email: preferences.email || undefined,
      metrics: preferences.metrics,
    })
    alert('保存成功')
    router.back()
  } catch (error: any) {
    console.error('Failed to save preferences:', error)
    alert(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.back()
}

onMounted(() => {
  pageView('/report-preferences')
  loadPreferences()
})
</script>

<style scoped lang="scss">
.preferences-page {
  padding: 24px;
  max-width: 720px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;

  h1 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
}

.form-section {
  margin-bottom: 32px;

  h3 {
    margin: 0 0 8px;
    font-size: 16px;
    color: var(--color-text);
  }

  .section-desc {
    margin: 0 0 16px;
    font-size: 13px;
    color: var(--color-text-secondary);
  }
}

.form-item {
  max-width: 400px;

  label {
    display: block;
    font-size: 13px;
    color: var(--color-text-secondary);
    margin-bottom: 6px;
  }
}

// Toggle Switch
.toggle-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toggle-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s;

  &:hover {
    border-color: var(--color-primary);
  }
}

.toggle-label {
  display: flex;
  flex-direction: column;
  gap: 2px;

  font-weight: 500;
  color: var(--color-text);

  .toggle-hint {
    font-size: 12px;
    color: var(--color-text-secondary);
    font-weight: normal;
  }
}

.toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: relative;
  width: 44px;
  height: 24px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  transition: 0.3s;

  &::before {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    background: white;
    border-radius: 50%;
    transition: 0.3s;
  }
}

.toggle-input:checked + .toggle-slider {
  background: var(--color-primary);
}

.toggle-input:checked + .toggle-slider::before {
  transform: translateX(20px);
}

// Checkbox Group
.checkbox-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s;

  &:hover {
    border-color: var(--color-primary);
  }

  input[type="checkbox"] {
    accent-color: var(--color-primary);
    width: 16px;
    height: 16px;
  }

  .checkbox-label {
    font-size: 13px;
    color: var(--color-text);
  }
}

// 通用
.loading-state,
.empty-state {
  text-align: center;
  padding: 60px;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border-radius: 12px;
}
</style>
