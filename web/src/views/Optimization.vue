<template>
  <div class="optimization-page">
    <div class="page-header">
      <div class="header-left">
        <h1>参数优化</h1>
        <p class="subtitle">自动搜索最优策略参数组合</p>
      </div>
      <div class="header-right">
        <button class="btn btn-primary" @click="showCreateDialog = true">
          + 新建优化任务
        </button>
      </div>
    </div>

    <div class="optimization-content">
      <!-- 任务列表 -->
      <div class="jobs-section">
        <div class="section-header">
          <h3>优化任务</h3>
          <div class="filter-controls">
            <select v-model="statusFilter" class="select-small">
              <option value="">全部状态</option>
              <option value="pending">等待中</option>
              <option value="running">运行中</option>
              <option value="completed">已完成</option>
              <option value="failed">失败</option>
              <option value="cancelled">已取消</option>
            </select>
          </div>
        </div>

        <div v-if="loadingJobs" class="loading-state">加载中...</div>
        <div v-else-if="jobs.length === 0" class="empty-state">
          <p>暂无优化任务，点击上方按钮创建</p>
        </div>
        <div v-else class="jobs-list">
          <div
            v-for="job in filteredJobs"
            :key="job.id"
            class="job-card"
            :class="job.status"
            @click="selectJob(job)"
          >
            <div class="job-header">
              <div class="job-title">{{ job.strategy }}</div>
              <div class="job-status" :class="job.status">{{ statusLabels[job.status] }}</div>
            </div>
            <div class="job-meta">
              <span>方法：{{ methodLabels[job.method] }}</span>
              <span>目标：{{ metricLabels[job.metric] }}</span>
              <span>试验：{{ job.completed_trials }}/{{ job.n_trials }}</span>
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: `${(job.completed_trials / job.n_trials) * 100}%` }"
              ></div>
            </div>
            <div class="job-time">
              {{ formatDate(job.created_at) }}
            </div>
          </div>
        </div>
      </div>

      <!-- 任务详情 -->
      <div v-if="selectedJob" class="detail-section">
        <div class="detail-header">
          <h3>任务详情</h3>
          <button class="btn btn-secondary btn-small" @click="selectedJob = null">关闭</button>
        </div>

        <div class="detail-content">
          <div class="info-grid">
            <div class="info-item">
              <label>策略</label>
              <span>{{ selectedJob.strategy }}</span>
            </div>
            <div class="info-item">
              <label>优化方法</label>
              <span>{{ methodLabels[selectedJob.method] }}</span>
            </div>
            <div class="info-item">
              <label>目标指标</label>
              <span>{{ metricLabels[selectedJob.metric] }}</span>
            </div>
            <div class="info-item">
              <label>状态</label>
              <span class="status-badge" :class="selectedJob.status">
                {{ statusLabels[selectedJob.status] }}
              </span>
            </div>
            <div class="info-item">
              <label>进度</label>
              <span>{{ selectedJob.completed_trials }} / {{ selectedJob.n_trials }}</span>
            </div>
            <div class="info-item">
              <label>并发</label>
              <span>{{ selectedJob.concurrent_limit || 4 }}</span>
            </div>
          </div>

          <!-- 最优参数 -->
          <div v-if="selectedJob.best_params" class="best-params">
            <h4>当前最优参数</h4>
            <pre class="params-json">{{ formatJson(selectedJob.best_params) }}</pre>
            <div v-if="selectedJob.best_metric !== null" class="best-metric">
              得分：{{ selectedJob.best_metric?.toFixed(4) }}
            </div>
          </div>

          <!-- 试验结果表格 -->
          <div class="trials-section">
            <h4>试验结果（Top 20）</h4>
            <div v-if="loadingTrials" class="loading-state">加载中...</div>
            <div v-else-if="trials.length === 0" class="empty-state">暂无试验数据</div>
            <div v-else class="trials-table-wrapper">
              <table class="trials-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th v-for="param in trialParams" :key="param">{{ param }}</th>
                    <th>得分</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(trial, _idx) in trials" :key="trial.trial_id" :class="trial.status">
                    <td>{{ trial.trial_id }}</td>
                    <td v-for="param in trialParams" :key="param">
                      {{ trial.params[param] }}
                    </td>
                    <td :class="trial.value >= 0 ? 'positive' : 'negative'">
                      {{ trial.value?.toFixed(4) }}
                    </td>
                    <td>
                      <span class="trial-status" :class="trial.status">
                        {{ trialStatusLabels[trial.status] }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建任务弹窗 -->
    <div v-if="showCreateDialog" class="modal-overlay" @click.self="showCreateDialog = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建参数优化任务</h3>
          <button class="close-btn" @click="showCreateDialog = false">×</button>
        </div>

        <div class="modal-body">
          <div class="form-section">
            <h4>基础配置</h4>
            <div class="form-row">
              <div class="form-item">
                <label>策略类型</label>
                <select v-model="newJob.strategy" class="select-full">
                  <option v-for="tpl in strategyTemplates" :key="tpl.name" :value="tpl.name">
                    {{ tpl.displayName }}
                  </option>
                </select>
              </div>
              <div class="form-item">
                <label>优化方法</label>
                <select v-model="newJob.method" class="select-full">
                  <option value="random">随机搜索</option>
                  <option value="bayesian">贝叶斯优化</option>
                </select>
              </div>
              <div class="form-item">
                <label>目标指标</label>
                <select v-model="newJob.metric" class="select-full">
                  <option value="sharpe">夏普比率</option>
                  <option value="total_return">总收益</option>
                  <option value="max_drawdown">最大回撤（最小化）</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-item">
                <label>试验次数</label>
                <input type="number" v-model.number="newJob.n_trials" class="input-number" min="10" max="500">
              </div>
              <div class="form-item">
                <label>并发数</label>
                <input type="number" v-model.number="newJob.concurrent_limit" class="input-number" min="1" max="10">
              </div>
            </div>
          </div>

          <div class="form-section">
            <h4>参数空间</h4>
            <div class="param-space">
              <div v-for="(param, key) in currentParamTemplate" :key="key" class="param-row">
                <div class="param-name">{{ param.label || key }}</div>
                <div class="param-inputs">
                  <input
                    type="number"
                    v-model.number="newJob.param_space[key].min"
                    placeholder="min"
                    class="input-small"
                  >
                  <span class="param-separator">-</span>
                  <input
                    type="number"
                    v-model.number="newJob.param_space[key].max"
                    placeholder="max"
                    class="input-small"
                  >
                  <span class="param-separator">step</span>
                  <input
                    type="number"
                    v-model.number="newJob.param_space[key].step"
                    placeholder="步长"
                    class="input-small"
                  >
                </div>
              </div>
            </div>
          </div>

          <div class="form-section">
            <h4>回测范围（可选）</h4>
            <div class="form-row">
              <div class="form-item">
                <label>股票代码</label>
                <input type="text" v-model="newJob.stock_code" placeholder="如：600519" class="input-full">
              </div>
              <div class="form-item">
                <label>开始日期</label>
                <input type="date" v-model="newJob.start_date" class="input-full">
              </div>
              <div class="form-item">
                <label>结束日期</label>
                <input type="date" v-model="newJob.end_date" class="input-full">
              </div>
              <div class="form-item">
                <label>初始资金</label>
                <input type="number" v-model.number="newJob.initial_capital" class="input-number" placeholder="100000">
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showCreateDialog = false">取消</button>
          <button class="btn btn-primary" @click="createJob" :disabled="creating">
            {{ creating ? '创建中...' : '创建任务' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, reactive, watch } from 'vue'
import { useAnalytics } from '@/composables/useAnalytics'
import { optimizationApi } from '@/api'

const { pageView } = useAnalytics()

// 状态
const jobs = ref<any[]>([])
const loadingJobs = ref(false)
const selectedJob = ref<any | null>(null)
const trials = ref<any[]>([])
const loadingTrials = ref(false)
const showCreateDialog = ref(false)
const creating = ref(false)

// 筛选
const statusFilter = ref('')

// 新建任务表单
const newJob = reactive({
  strategy: 'ma_crossover',
  method: 'bayesian' as 'random' | 'bayesian',
  metric: 'sharpe' as 'sharpe' | 'total_return' | 'max_drawdown',
  n_trials: 50,
  concurrent_limit: 4,
  param_space: {} as Record<string, { min: number; max: number; step: number }>,
  stock_code: '',
  start_date: '',
  end_date: '',
  initial_capital: 100000,
})

// 模板参数定义（根据策略类型动态变化）
interface ParamDef {
  min: number
  max: number
  step: number
  label?: string
}

const paramTemplates: Record<string, Record<string, ParamDef>> = {
  ma_crossover: {
    short_period: { min: 5, max: 20, step: 1, label: '短周期' },
    long_period: { min: 20, max: 60, step: 1, label: '长周期' },
  },
  rsi_strategy: {
    rsi_period: { min: 6, max: 30, step: 1, label: 'RSI 周期' },
    oversold: { min: 10, max: 40, step: 1, label: '超卖线' },
    overbought: { min: 60, max: 90, step: 1, label: '超买线' },
  },
}

// 策略模板列表（用于下拉选择）
const strategyTemplates = computed(() => {
  return Object.entries(paramTemplates).map(([key, params]) => ({
    name: key,
    displayName: getStrategyDisplayName(key),
    parameters: Object.entries(params).map(([k, v]) => ({
      name: k,
      label: v.label || k,
      type: 'number' as const,
    })),
  }))
})

function getStrategyDisplayName(key: string): string {
  const names: Record<string, string> = {
    ma_crossover: '均线交叉',
    rsi_strategy: 'RSI 策略',
  }
  return names[key] || key
}

// 计算属性
const filteredJobs = computed(() => {
  if (!statusFilter.value) return jobs.value
  return jobs.value.filter(job => job.status === statusFilter.value)
})

const trialParams = computed(() => {
  if (!trials.value.length) return []
  return Object.keys(trials.value[0].params || {})
})

const currentParamTemplate = computed((): Record<string, ParamDef> => {
  return paramTemplates[newJob.strategy] || {}
})

// 同步参数空间模板到 newJob.param_space
watch(
  () => newJob.strategy,
  (newStrategy) => {
    const template = paramTemplates[newStrategy]
    if (template) {
      // 重置 param_space 为模板默认值
      Object.keys(newJob.param_space).forEach(key => delete newJob.param_space[key])
      Object.entries(template).forEach(([key, def]) => {
        newJob.param_space[key] = { min: def.min, max: def.max, step: def.step }
      })
    }
  },
  { immediate: true }
)

// 标签
const statusLabels: Record<string, string> = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

const methodLabels: Record<string, string> = {
  random: '随机搜索',
  bayesian: '贝叶斯优化',
}

const metricLabels: Record<string, string> = {
  sharpe: '夏普比率',
  total_return: '总收益',
  max_drawdown: '最大回撤',
}

const trialStatusLabels: Record<string, string> = {
  pending: '等待',
  running: '运行中',
  completed: '完成',
  failed: '失败',
}

// 方法
async function loadJobs() {
  loadingJobs.value = true
  try {
    const res = await optimizationApi.listJobs({ limit: 20 })
    jobs.value = (res.data?.items || []).sort((a: any, b: any) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  } catch (error) {
    console.error('Failed to load jobs:', error)
  } finally {
    loadingJobs.value = false
  }
}

async function selectJob(job: any) {
  selectedJob.value = job
  await loadTrials(job.id)
}

async function loadTrials(jobId: string) {
  loadingTrials.value = true
  try {
    const res = await optimizationApi.getTrials(jobId, { limit: 20 })
    trials.value = (res.data?.items || []).sort((a: any, b: any) => b.trial_id - a.trial_id)
  } catch (error) {
    console.error('Failed to load trials:', error)
    trials.value = []
  } finally {
    loadingTrials.value = false
  }
}

async function createJob() {
  creating.value = true
  try {
    const res = await optimizationApi.createJob({
      strategy: newJob.strategy,
      param_space: newJob.param_space,
      method: newJob.method,
      metric: newJob.metric,
      n_trials: newJob.n_trials,
      concurrent_limit: newJob.concurrent_limit,
      stock_code: newJob.stock_code || undefined,
      start_date: newJob.start_date || undefined,
      end_date: newJob.end_date || undefined,
      initial_capital: newJob.initial_capital,
    })
    showCreateDialog.value = false
    await loadJobs()
    // 自动选中新任务
    const newJobData = res.data
    if (newJobData?.id) {
      await selectJob(newJobData)
    }
  } catch (error: any) {
    console.error('Failed to create job:', error)
    alert(`创建失败：${error.response?.data?.detail || error.message}`)
  } finally {
    creating.value = false
  }
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function formatJson(obj: any) {
  return JSON.stringify(obj, null, 2)
}

onMounted(() => {
  pageView('/optimization')
  loadJobs()
})

// 轮询更新运行中的任务
let pollTimer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  pollTimer = setInterval(() => {
    if (jobs.value.some(j => j.status === 'running')) {
      loadJobs()
      if (selectedJob.value) {
        selectJob(selectedJob.value)
      }
    }
  }, 5000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped lang="scss">
.optimization-page {
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

.optimization-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

// 任务卡片
.jobs-section {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      margin: 0;
      font-size: 18px;
      color: rgba(255, 255, 255, 0.8);
    }
  }
}

.jobs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.job-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--color-primary);
    transform: translateY(-2px);
  }

  &.running {
    border-left: 3px solid #00C853;
  }

  &.completed {
    border-left: 3px solid #2196F3;
  }

  &.failed {
    border-left: 3px solid #FF1744;
  }
}

.job-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;

  .job-title {
    font-weight: 600;
    color: var(--color-text);
  }

  .job-status {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.1);

    &.running { background: rgba(0, 200, 83, 0.2); color: #00C853; }
    &.completed { background: rgba(33, 150, 243, 0.2); color: #2196F3; }
    &.failed { background: rgba(255, 23, 68, 0.2); color: #FF1744; }
  }
}

.job-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}

.progress-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
    transition: width 0.3s;
  }
}

.job-time {
  font-size: 12px;
  color: var(--color-text-secondary);
}

// 详情区域
.detail-section {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h3 {
      margin: 0;
      font-size: 18px;
    }
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;

    label {
      font-size: 12px;
      color: var(--color-text-secondary);
      text-transform: uppercase;
    }

    span {
      font-size: 14px;
      color: var(--color-text);
    }
  }
}

.best-params {
  background: var(--color-bg-primary);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;

  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    color: var(--color-text-secondary);
  }

  .params-json {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 12px;
    color: var(--color-text);
    background: rgba(0, 0, 0, 0.3);
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 0;
  }

  .best-metric {
    margin-top: 12px;
    font-size: 16px;
    font-weight: 600;
    color: var(--color-accent);
  }
}

.trials-section {
  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    color: var(--color-text-secondary);
  }
}

.trials-table-wrapper {
  overflow-x: auto;
}

.trials-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th, td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid var(--color-border);
  }

  th {
    background: var(--color-bg-primary);
    color: var(--color-text-secondary);
    font-weight: 600;
  }

  tr:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .positive {
    color: #00C853;
  }

  .negative {
    color: #FF1744;
  }
}

.trial-status {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);

  &.running { background: rgba(0, 200, 83, 0.2); color: #00C853; }
  &.completed { background: rgba(33, 150, 243, 0.2); color: #2196F3; }
  &.failed { background: rgba(255, 23, 68, 0.2); color: #FF1744; }
}

// Modal
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--color-bg-secondary);
  border-radius: 12px;
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid var(--color-border);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--color-border);

  h3 {
    margin: 0;
    font-size: 18px;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 24px;
    color: var(--color-text-secondary);
    cursor: pointer;
    padding: 0;

    &:hover {
      color: var(--color-text);
    }
  }
}

.modal-body {
  padding: 20px;
}

.form-section {
  margin-bottom: 24px;

  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    color: var(--color-text-secondary);
    text-transform: uppercase;
  }
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 13px;
    color: var(--color-text-secondary);
  }
}

.param-space {
  .param-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--color-border);

    &:last-child {
      border-bottom: none;
    }
  }

  .param-name {
    font-weight: 500;
    width: 120px;
  }

  .param-inputs {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    max-width: 400px;
  }

  .param-separator {
    color: var(--color-text-secondary);
  }
}

.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 通用
.loading-state,
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border-radius: 8px;
}
</style>
