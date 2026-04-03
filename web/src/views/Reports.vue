<template>
  <div class="reports-page">
    <div class="page-header">
      <div class="header-left">
        <h1>数据洞察报告</h1>
        <p class="subtitle">查看和分析您的投资数据报告</p>
      </div>
      <div class="header-right">
        <button class="btn btn-primary" @click="generateReport" :disabled="generating">
          {{ generating ? '生成中...' : '生成报告' }}
        </button>
        <router-link to="/report-preferences" class="btn btn-secondary">
          偏好设置
        </router-link>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filters-bar">
      <div class="filter-group">
        <label>报告类型</label>
        <div class="filter-buttons">
          <button
            v-for="type in reportTypes"
            :key="type.value"
            class="filter-btn"
            :class="{ active: filters.type === type.value }"
            @click="filters.type = type.value || ''"
          >
            {{ type.label }}
          </button>
        </div>
      </div>

      <div class="filter-group">
        <label>状态</label>
        <div class="filter-buttons">
          <button
            v-for="status in statusOptions"
            :key="status.value"
            class="filter-btn"
            :class="{ active: filters.status === status.value }"
            @click="filters.status = status.value || ''"
          >
            {{ status.label }}
          </button>
        </div>
      </div>

      <div class="filter-group">
        <label>时间范围</label>
        <select v-model="filters.days" class="select-small">
          <option value="7">近 7 天</option>
          <option value="30">近 30 天</option>
          <option value="90">近 90 天</option>
          <option value="0">全部</option>
        </select>
      </div>
    </div>

    <!-- 报告列表 -->
    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="reports.length === 0" class="empty-state">
      <p>暂无报告</p>
      <button class="btn btn-primary btn-small" @click="generateReport">创建第一份报告</button>
    </div>
    <div v-else class="reports-grid">
      <div
        v-for="report in reports"
        :key="report.id"
        class="report-card"
        :class="report.status"
        @click="viewReport(report.id)"
      >
        <div class="report-header">
          <div class="report-type-badge" :class="report.type">
            {{ typeLabels[report.type] }}
          </div>
          <div class="report-status" :class="report.status">
            {{ statusLabels[report.status] }}
          </div>
        </div>

        <div class="report-title">{{ report.title }}</div>

        <div class="report-meta">
          <span>生成时间：{{ formatDate(report.generated_at) }}</span>
          <span>数据日期：{{ report.data_date }}</span>
        </div>

        <div v-if="report.summary" class="report-summary">
          <div class="summary-item">
            <span class="label">总收益</span>
            <span class="value" :class="report.summary.total_return >= 0 ? 'positive' : 'negative'">
              {{ formatPercent(report.summary.total_return) }}
            </span>
          </div>
          <div class="summary-item">
            <span class="label">夏普比率</span>
            <span class="value">{{ report.summary.sharpe_ratio?.toFixed(2) }}</span>
          </div>
          <div class="summary-item">
            <span class="label">最大回撤</span>
            <span class="value negative">{{ formatPercent(report.summary.max_drawdown) }}</span>
          </div>
        </div>

        <div class="report-actions">
          <button class="btn btn-secondary btn-small" @click.stop="viewReport(report.id)">
            查看详情
          </button>
          <button
            v-if="report.status === 'generated'"
            class="btn btn-secondary btn-small"
            @click.stop="downloadReport(report)"
          >
            下载
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalytics } from '@/composables/useAnalytics'
import { reportApi } from '@/api'

const router = useRouter()
const { pageView } = useAnalytics()

// 状态
const reports = ref<any[]>([])
const loading = ref(false)
const generating = ref(false)

// 筛选条件
const filters = reactive({
  type: '' as '' | 'daily' | 'weekly' | 'monthly',
  status: '' as '' | 'generated' | 'generating' | 'failed',
  days: '30',
})

// 选项
const reportTypes = [
  { label: '全部类型', value: '' },
  { label: '日报', value: 'daily' },
  { label: '周报', value: 'weekly' },
  { label: '月报', value: 'monthly' },
] as const

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '已生成', value: 'generated' },
  { label: '生成中', value: 'generating' },
  { label: '失败', value: 'failed' },
] as const

const typeLabels: Record<string, string> = {
  daily: '日报',
  weekly: '周报',
  monthly: '月报',
}

const statusLabels: Record<string, string> = {
  generated: '已生成',
  generating: '生成中',
  failed: '失败',
}

// 方法
async function loadReports() {
  loading.value = true
  try {
    const params: any = {}
    if (filters.type) params.type = filters.type
    if (filters.status) params.status = filters.status
    if (filters.days !== '0') {
      const start = new Date()
      start.setDate(start.getDate() - Number(filters.days))
      params.start_date = start.toISOString().split('T')[0]
    }

    const res = await reportApi.list(params)
    reports.value = (res.data?.items || []).sort(
      (a: any, b: any) => new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime()
    )
  } catch (error) {
    console.error('Failed to load reports:', error)
  } finally {
    loading.value = false
  }
}

async function generateReport() {
  generating.value = true
  try {
    // 默认生成日报
    await reportApi.generate({ type: 'daily' })
    await loadReports()
  } catch (error: any) {
    console.error('Failed to generate report:', error)
    alert(`生成失败：${error.response?.data?.detail || error.message}`)
  } finally {
    generating.value = false
  }
}

function viewReport(reportId: string) {
  router.push(`/reports/${reportId}`)
}

function downloadReport(report: any) {
  // 如果报告有 HTML 内容，打开新窗口打印
  if (report.html_content) {
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(report.html_content)
      printWindow.document.close()
      printWindow.print()
    }
  }
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return '-'
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
}

// 监听筛选变化
watch(filters, () => {
  loadReports()
})

onMounted(() => {
  pageView('/reports')
  loadReports()
})
</script>

<style scoped lang="scss">
.reports-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }
}

// 筛选栏
.filters-bar {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--color-bg-secondary);
  border-radius: 10px;
  flex-wrap: wrap;

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 8px;

    label {
      font-size: 12px;
      color: var(--color-text-secondary);
      text-transform: uppercase;
    }
  }

  .filter-buttons {
    display: flex;
    gap: 8px;
  }

  .filter-btn {
    padding: 6px 12px;
    border: 1px solid var(--color-border);
    background: var(--color-bg-primary);
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    color: var(--color-text);
    transition: all 0.2s;

    &:hover {
      border-color: var(--color-primary);
    }

    &.active {
      background: var(--color-primary);
      color: white;
      border-color: var(--color-primary);
    }
  }
}

// 报告网格
.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.report-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--color-primary);
    transform: translateY(-2px);
  }

  &.generating {
    border-left: 3px solid #FF9800;
  }

  &.generated {
    border-left: 3px solid #4CAF50;
  }

  &.failed {
    border-left: 3px solid #F44336;
  }
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.report-type-badge {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
  font-weight: 600;

  &.daily { background: rgba(33, 150, 243, 0.2); color: #2196F3; }
  &.weekly { background: rgba(76, 175, 80, 0.2); color: #4CAF50; }
  &.monthly { background: rgba(156, 39, 176, 0.2); color: #9C27B0; }
}

.report-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);

  &.generated { background: rgba(76, 175, 80, 0.2); color: #4CAF50; }
  &.generating { background: rgba(255, 152, 0, 0.2); color: #FF9800; }
  &.failed { background: rgba(244, 67, 54, 0.2); color: #F44336; }
}

.report-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 8px;
}

.report-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 16px;
}

.report-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 12px;
  background: var(--color-bg-primary);
  border-radius: 8px;
  margin-bottom: 16px;

  .summary-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;

    .label {
      font-size: 11px;
      color: var(--color-text-secondary);
    }

    .value {
      font-size: 14px;
      font-weight: 600;
      color: var(--color-text);

      &.positive { color: #00C853; }
      &.negative { color: #FF1744; }
    }
  }
}

.report-actions {
  display: flex;
  gap: 8px;
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
