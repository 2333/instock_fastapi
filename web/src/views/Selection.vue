<template>
  <div class="selection-page">
    <div class="page-header">
      <div class="header-left">
        <span class="eyebrow">M3 参数化筛选</span>
        <h1>选股扫描台</h1>
        <p class="subtitle">先设置条件，再点击开始筛选；修改条件不会自动生效。</p>
      </div>
      <div class="header-right">
        <button class="btn btn-primary btn-hero" @click="runSelection" :disabled="loading">
          {{ loading ? '运行中...' : '开始筛选' }}
        </button>
        <div class="secondary-actions">
          <button class="btn btn-secondary" @click="saveCriteria">保存筛选器</button>
          <button class="btn btn-secondary" @click="saveCurrentStrategy" :disabled="savingStrategy">
            {{ savingStrategy ? '保存中...' : '保存为策略' }}
          </button>
          <button
            class="btn btn-secondary"
            @click="saveStrategyAndGoBacktest"
            :disabled="savingStrategy || !hasResults"
          >
            {{ savingStrategy ? '保存中...' : '保存并去回测' }}
          </button>
          <button class="btn btn-quiet" @click="toggleCriteriaPanel">
            {{ criteriaCollapsed ? '展开条件' : '收起条件' }}
          </button>
        </div>
      </div>
    </div>

    <section class="workflow-guide" aria-label="选股使用步骤">
      <div class="workflow-step active">
        <span class="step-index">1</span>
        <div>
          <strong>设置条件</strong>
          <p>全部字段都是可选；不填写就是不限。</p>
        </div>
      </div>
      <div class="workflow-step">
        <span class="step-index">2</span>
        <div>
          <strong>开始筛选</strong>
          <p>只有点击“开始筛选”才会执行扫描。</p>
        </div>
      </div>
      <div class="workflow-step">
        <span class="step-index">3</span>
        <div>
          <strong>保存与订阅</strong>
          <p>满意后保存筛选器，再创建盘后订阅。</p>
        </div>
      </div>
    </section>

    <div class="selection-layout">
      <aside
        v-show="!criteriaCollapsed"
        ref="criteriaPanelRef"
        class="criteria-panel"
        :style="{ width: `${criteriaPanelWidth}px` }"
      >
        <div class="panel-section start-section">
          <div class="section-heading">
            <h3>从这里开始</h3>
            <p>建议先只设置 1-2 个条件，运行后再逐步增加。当前已启用 {{ activeFilterCount }} 个条件。</p>
          </div>
          <div class="effect-note">
            <span>不会自动扫描</span>
            <strong>调整任意字段后，请点击右上角“开始筛选”。</strong>
          </div>
          <div class="default-note">
            <span>默认参数</span>
            <strong>RSI 14 / MACD 12-26-9 / BOLL 20, 2.0</strong>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-heading">
            <h3>1. 基础范围</h3>
            <p>这些字段都不是必填；留空表示不限。</p>
          </div>
          <div class="criteria-group">
            <label>
              <span>市场范围</span>
              <em>可选 · 默认全部市场</em>
            </label>
            <select v-model="criteria.market" class="filter-select criteria-select">
              <option value="">全部市场</option>
              <option
                v-for="option in marketOptions"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-heading">
            <h3>2. 价格与涨跌幅</h3>
            <p>填一个边界也可以，例如只填“最小价格”。</p>
          </div>
          <div class="criteria-group">
            <label>
              <span>价格范围</span>
              <em>可选 · 不填不限</em>
            </label>
            <div class="range-inputs">
              <input
                type="number"
                v-model.number="criteria.priceMin"
                placeholder="最小"
                class="input-small"
                :class="{ invalid: priceMinInvalid, valid: priceMinValid }"
              >
              <span>-</span>
              <input
                type="number"
                v-model.number="criteria.priceMax"
                placeholder="最大"
                class="input-small"
                :class="{ invalid: priceMaxInvalid, valid: priceMaxValid }"
              >
            </div>
            <div v-if="priceRangeError" class="criteria-hint error">{{ priceRangeError }}</div>
          </div>

          <div class="criteria-group">
            <label>
              <span>日涨跌 (%)</span>
              <em>可选 · -100 到 100</em>
            </label>
            <div class="range-inputs">
              <input
                type="number"
                v-model.number="criteria.changeMin"
                placeholder="最小"
                class="input-small"
                :class="{ invalid: changeMinInvalid, valid: changeMinValid }"
              >
              <span>-</span>
              <input
                type="number"
                v-model.number="criteria.changeMax"
                placeholder="最大"
                class="input-small"
                :class="{ invalid: changeMaxInvalid, valid: changeMaxValid }"
              >
            </div>
            <div v-if="changeRangeError" class="criteria-hint error">{{ changeRangeError }}</div>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-heading">
            <h3>3. 技术指标参数</h3>
            <p>默认参数已经填好。只有勾选信号或填写上下限后，对应指标才参与筛选。</p>
          </div>

          <div class="criteria-group">
            <label>
              <span>RSI 范围</span>
              <em>可选 · 默认周期 {{ getParamDefaultText('rsiMin', 'period', 14) }}</em>
            </label>
            <div class="range-inputs">
              <input
                type="number"
                v-model.number="criteria.rsiMin"
                placeholder="最小"
                min="0"
                max="100"
                class="input-small"
                :class="{ invalid: rsiMinInvalid, valid: rsiMinValid }"
              >
              <span>-</span>
              <input
                type="number"
                v-model.number="criteria.rsiMax"
                placeholder="最大"
                min="0"
                max="100"
                class="input-small"
                :class="{ invalid: rsiMaxInvalid, valid: rsiMaxValid }"
              >
            </div>
            <div v-if="rsiRangeError" class="criteria-hint error">{{ rsiRangeError }}</div>
            <div class="param-grid single-column">
              <label class="param-field">
                <span>RSI 周期</span>
                <input
                  type="number"
                  v-model.number="indicatorParams.rsiPeriod"
                  class="input-small"
                  :min="getParamBounds('rsiMin', 'period').min"
                  :max="getParamBounds('rsiMin', 'period').max"
                >
              </label>
            </div>
            <div v-if="rsiPeriodError" class="criteria-hint error">{{ rsiPeriodError }}</div>
            <p class="field-hint">RSI 相对强弱指标，通常 0-100，超卖区域低于 30</p>
          </div>

          <div class="criteria-group">
            <label>
              <span>MACD 信号</span>
              <em>可选 · 默认 {{ getMacdDefaultText() }}</em>
            </label>
            <div class="checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="criteria.macdBullish">
                只看 MACD 看涨（金叉倾向）
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="criteria.macdBearish">
                只看 MACD 看跌（死叉倾向）
              </label>
            </div>
            <div class="param-grid">
              <label class="param-field">
                <span>快线</span>
                <input
                  type="number"
                  v-model.number="indicatorParams.macdFastPeriod"
                  class="input-small"
                  :min="getParamBounds('macdBullish', 'fast_period').min"
                  :max="getParamBounds('macdBullish', 'fast_period').max"
                >
              </label>
              <label class="param-field">
                <span>慢线</span>
                <input
                  type="number"
                  v-model.number="indicatorParams.macdSlowPeriod"
                  class="input-small"
                  :min="getParamBounds('macdBullish', 'slow_period').min"
                  :max="getParamBounds('macdBullish', 'slow_period').max"
                >
              </label>
              <label class="param-field">
                <span>信号</span>
                <input
                  type="number"
                  v-model.number="indicatorParams.macdSignalPeriod"
                  class="input-small"
                  :min="getParamBounds('macdBullish', 'signal_period').min"
                  :max="getParamBounds('macdBullish', 'signal_period').max"
                >
              </label>
            </div>
            <div v-if="macdParameterError" class="criteria-hint error">{{ macdParameterError }}</div>
            <p class="field-hint">MACD 柱状图是否为正（看涨）或为负（看跌）</p>
          </div>

          <div class="criteria-group">
            <label>
              <span>BOLL 通道</span>
              <em>可选 · 默认 {{ getBollDefaultText() }}</em>
            </label>
            <div class="checkbox-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="criteria.bollCloseAboveUpper">
                收盘价突破上轨
              </label>
              <label class="checkbox-label">
                <input type="checkbox" v-model="criteria.bollCloseBelowLower">
                收盘价跌破下轨
              </label>
            </div>
            <div class="param-grid">
              <label class="param-field">
                <span>BOLL 周期</span>
                <input
                  type="number"
                  v-model.number="indicatorParams.bollPeriod"
                  class="input-small"
                  :min="getParamBounds('bollCloseAboveUpper', 'period').min"
                  :max="getParamBounds('bollCloseAboveUpper', 'period').max"
                >
              </label>
              <label class="param-field">
                <span>标准差</span>
                <input
                  type="number"
                  v-model.number="indicatorParams.bollStddev"
                  class="input-small"
                  :min="getParamBounds('bollCloseAboveUpper', 'stddev').min"
                  :max="getParamBounds('bollCloseAboveUpper', 'stddev').max"
                  step="0.1"
                >
              </label>
            </div>
            <div v-if="bollParameterError" class="criteria-hint error">{{ bollParameterError }}</div>
            <p class="field-hint">BOLL 默认使用 20 周期、2.0 倍标准差，可调整为更敏感或更保守的通道。</p>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-heading">
            <h3>4. 形态条件</h3>
            <p>可与价格、涨跌幅、指标组合；不选则不限形态。</p>
          </div>
          <div class="criteria-group">
            <label>
              <span>形态</span>
              <em>可选 · 默认不限</em>
            </label>
            <select v-model="criteria.pattern" class="filter-select criteria-select">
              <option value="">不限形态</option>
              <option v-for="pattern in patternOptions" :key="pattern.value" :value="pattern.value">
                {{ pattern.label }}
              </option>
            </select>
            <p class="field-hint">命中后会写入结果证据，例如锤子线、头肩底、双底等。</p>
          </div>
        </div>

        <div class="panel-section utility-section">
          <div class="section-heading">
            <h3>快捷入口</h3>
            <p>模板和已保存筛选器只会填表，不会自动扫描。</p>
          </div>

          <div v-if="templatesCollapsed" class="templates-collapsed-bar">
            <button class="btn btn-small" @click="setTemplatesCollapsed(false)">展开快捷模板</button>
          </div>

          <template v-else>
            <div class="templates-section">
              <div v-if="templatesLoading" class="templates-loading">加载中...</div>
              <div v-else class="templates-grid">
                <button
                  v-for="tpl in templates"
                  :key="tpl.id"
                  class="template-card"
                  @click="applyTemplate(tpl)"
                >
                  <span class="template-icon">{{ tpl.icon }}</span>
                  <span class="template-name">{{ tpl.name }}</span>
                  <span class="template-desc">{{ tpl.description }}</span>
                </button>
              </div>
              <button class="templates-toggle" @click="setTemplatesCollapsed(true)">收起模板</button>
            </div>

            <div v-if="recentTemplates.length" class="recent-templates-section">
              <h4>最近使用</h4>
              <div class="recent-templates-grid">
                <button
                  v-for="tpl in recentTemplates"
                  :key="tpl.id"
                  class="template-card recent-template-card"
                  @click="applyTemplate(tpl)"
                >
                  <span class="template-icon">{{ tpl.icon }}</span>
                  <span class="template-name">{{ tpl.name }}</span>
                </button>
              </div>
            </div>
          </template>

          <div v-if="myConditions.length" class="saved-conditions-section">
            <div class="section-heading compact-heading">
              <h4>已保存筛选器</h4>
              <p>点击名称加载到表单；触发用于运行已订阅提醒。</p>
            </div>
            <div class="saved-conditions-list">
              <div
                v-for="cond in myConditions"
                :key="cond.id"
                class="saved-condition-item"
              >
                <button class="saved-condition-main" @click="loadSavedCondition(cond)">
                  <span class="saved-condition-name">{{ cond.name }}</span>
                  <span :class="['saved-condition-category', categoryClass(cond.category)]">
                    {{ cond.category || 'custom' }}
                  </span>
                </button>
                <div class="saved-condition-actions">
                  <button
                    class="btn btn-small"
                    :disabled="subscriptionBusyId === cond.id"
                    @click="ensureSubscription(cond)"
                  >
                    {{ getSubscriptionForCondition(cond.id) ? '已订阅' : '订阅' }}
                  </button>
                  <button
                    class="btn btn-small btn-primary"
                    :disabled="!getSubscriptionForCondition(cond.id) || subscriptionBusyId === cond.id"
                    @click="triggerSubscription(cond)"
                  >
                    {{ subscriptionBusyId === cond.id ? '运行中' : '触发' }}
                  </button>
                </div>
                <div v-if="getSubscriptionForCondition(cond.id)?.status === 'stale'" class="subscription-note warning">
                  订阅已失效，请重新保存后订阅
                </div>
                <div v-else-if="lastSubscriptionRunByCondition[cond.id]" class="subscription-note">
                  {{ lastSubscriptionRunByCondition[cond.id] }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="panel-section">
          <div class="section-heading">
            <h3>暂不可用条件</h3>
            <p>以下条件暂未接入，不会参与当前筛选。</p>
          </div>
          <div class="legacy-grid">
            <section
              v-for="group in unavailableFilterGroups"
              :key="group.title"
              class="legacy-card"
            >
              <h4>{{ group.title }}</h4>
              <ul class="legacy-list">
                <li v-for="item in group.items" :key="item">{{ item }}</li>
              </ul>
            </section>
          </div>
        </div>
      </aside>

      <div
        v-show="!criteriaCollapsed"
        class="panel-resizer"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整筛选条件宽度"
        @mousedown="startCriteriaResize"
        @touchstart.prevent="startCriteriaResize"
      ></div>

      <main class="results-panel">
        <div
          class="scan-status-card"
          :class="{ dirty: criteriaDirty, complete: hasRunOnce && !criteriaDirty && !scanError, error: !!scanError }"
        >
          <div>
            <strong>{{ scanStatusTitle }}</strong>
            <p>{{ scanStatusDescription }}</p>
          </div>
          <button class="btn btn-primary" @click="runSelection" :disabled="loading">
            {{ loading ? '运行中...' : '开始筛选' }}
          </button>
        </div>

        <div class="availability-note">
          <strong>当前能力</strong>
          <span>{{ supportedFiltersDescription }}</span>
        </div>

        <div v-if="!hasResults" class="empty-state">
          <div class="empty-icon">🎯</div>
          <h3>{{ emptyStateTitle }}</h3>
          <p>{{ emptyStateDescription }}</p>
          <ul v-if="scanError" class="empty-suggestions">
            <li>页面不会继续展示上一次结果，避免误判</li>
            <li>可以直接重新执行，或稍后再试</li>
            <li>如果持续失败，请检查后端接口或数据服务状态</li>
          </ul>
          <ul v-else-if="hasRunOnce" class="empty-suggestions">
            <li>放宽价格或涨跌幅范围</li>
            <li>减少条件数量（同时满足过多条件可能导致零命中）</li>
            <li>检查市场数据是否已更新（盘后运行）</li>
            <li>切换至"形态"或"指标"条件，增加命中机会</li>
          </ul>
          <ul v-else class="empty-suggestions onboarding-suggestions">
            <li>没有必填项；不填写表示不限</li>
            <li>模板只负责填入条件，不会立即扫描</li>
            <li>RSI/MACD/BOLL 参数只有在对应条件启用后参与计算</li>
          </ul>
          <button v-if="scanError" class="btn btn-primary" @click="runSelection" :disabled="loading">
            {{ loading ? '运行中...' : '重新筛选' }}
          </button>
          <button v-else-if="hasRunOnce" class="btn btn-secondary" @click="resetCriteria">重置条件</button>
          <button v-else class="btn btn-primary" @click="runSelection" :disabled="loading">
            {{ loading ? '运行中...' : '开始筛选' }}
          </button>
        </div>

        <template v-else>
          <div class="results-header">
            <div class="results-summary">
              <span class="results-count">共 {{ screeningSummary.total }} 只股票</span>
              <span v-if="screeningSummary.tradeDate" class="results-date">
                筛选交易日 {{ formatDisplayDate(screeningSummary.tradeDate) }}
              </span>
            </div>
            <div class="results-actions">
              <select v-model="sortBy" class="filter-select">
                <option value="score">按评分排序</option>
                <option value="date">按日期排序</option>
              </select>
              <button
                v-if="!compareMode"
                class="btn btn-secondary"
                @click="enableCompareMode"
              >
                对比结果
              </button>
              <button
                v-else
                class="btn btn-primary"
                :disabled="selectedHistoryIds.size < 2"
                @click="startCompare"
              >
                对比选中 ({{ selectedHistoryIds.size }})
              </button>
              <button
                v-if="compareMode"
                class="btn btn-secondary"
                @click="exitCompareMode"
              >
                取消
              </button>
            </div>
          </div>

          <div v-if="sortedResults.length > pageSize" class="results-pagination">
            <span class="pagination-info">共 {{ sortedResults.length }} 条，显示第 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, sortedResults.length) }} 条</span>
            <div class="pagination-controls">
              <button
                class="pagination-btn"
                :disabled="currentPage === 1"
                @click="currentPage--"
              >上一页</button>
              <span class="pagination-pages">
                <button
                  v-for="page in visiblePages"
                  :key="page"
                  class="pagination-page"
                  :class="{ active: page === currentPage }"
                  @click="currentPage = page"
                >{{ page }}</button>
              </span>
              <button
                class="pagination-btn"
                :disabled="currentPage === totalPages"
                @click="currentPage++"
              >下一页</button>
            </div>
          </div>

          <div class="results-table-wrapper">
            <table class="results-table">
              <thead>
                <tr>
                  <th v-if="compareMode" style="width: 48px;">
                    <input
                      type="checkbox"
                      :checked="allCurrentSelectionIdsSelected"
                      @change="toggleSelectAll"
                      title="全选"
                    />
                  </th>
                  <th>代码</th>
                  <th>名称</th>
                  <th>评分</th>
                  <th>命中原因</th>
                  <th>验证入口</th>
                  <th>日期</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="stock in paginatedResults"
                  :key="stock.code"
                  :class="{ 'row-selected': compareMode && selectedHistoryIds.has(extractSelectionId(stock)) }"
                  @click="compareMode ? handleRowClick(stock) : openStockDetail(stock)"
                >
                  <td v-if="compareMode" @click.stop>
                    <input
                      type="checkbox"
                      :checked="selectedHistoryIds.has(extractSelectionId(stock))"
                      @change="toggleSelection(extractSelectionId(stock))"
                    />
                  </td>
                  <td class="stock-code">{{ stock.code }}</td>
                  <td class="stock-name">{{ stock.name || '-' }}</td>
                  <td>{{ stock.score }}</td>
                  <td class="reason-cell">
                    <div class="reason-summary">{{ stock.reason_summary || '已命中筛选条件' }}</div>
                    <div v-if="stock.evidence.length" class="evidence-list">
                      <span
                        v-for="item in stock.evidence.slice(0, 3)"
                        :key="`${stock.code}-${item.key}`"
                        class="evidence-chip"
                      >
                        {{ formatEvidence(item) }}
                      </span>
                    </div>
                  </td>
                  <td>
                    <button class="detail-link" @click.stop="openStockDetail(stock)">
                      查看验证
                    </button>
                    <button class="watchlist-link" @click.stop="addToWatchlist(stock.code)">
                      加入关注
                    </button>
                  </td>
                  <td>{{ stock.date || stock.trade_date }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </main>
    </div>
  </div>

  <!-- Comparison Modal -->
  <div v-if="showCompareModal" class="modal-overlay" @click.self="showCompareModal = false">
    <div class="modal-content comparison-modal">
      <div class="modal-header">
        <h3>对比结果 ({{ comparisonResults.length }} 个筛选)</h3>
        <button class="close-btn" @click="showCompareModal = false">×</button>
      </div>
      <div class="modal-body">
        <div v-if="comparisonResults.length === 0" class="empty-state">
          无数据
        </div>
        <div v-else class="comparison-grid">
          <div
            v-for="item in comparisonResults"
            :key="item.history_id"
            class="comparison-card"
          >
            <div class="card-header">
              <div class="card-title">筛选 {{ item.history_id.slice(-8) }}</div>
              <div class="card-subtitle">{{ formatDisplayDate(item.trade_date) }}</div>
            </div>
            <div class="card-stats">
              <div class="stat">
                <span class="stat-label">股票数</span>
                <span class="stat-value">{{ item.total }}</span>
              </div>
              <div class="stat">
                <span class="stat-label">平均分</span>
                <span class="stat-value">{{ item.avg_score?.toFixed(2) }}</span>
              </div>
            </div>
            <div class="card-top-stocks">
              <h4>Top 5</h4>
              <ul>
                <li v-for="stock in item.top_stocks" :key="stock.code">
                  <span class="stock-code">{{ stock.code }}</span>
                  <span class="stock-name">{{ stock.name }}</span>
                  <span class="stock-score">{{ stock.score?.toFixed(2) }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, inject, watch } from 'vue'
import { useRouter } from 'vue-router'
import { alertSubscriptionApi, attentionApi, selectionApi, strategyApi } from '@/api'
import { useAnalytics } from '@/composables/useAnalytics'
import { useResizablePanel } from '@/composables/useResizablePanel'

interface ScreeningEvidenceItem {
  key: string
  label: string
  value: string | number | boolean | null
  operator?: string | null
  condition?: string | number | boolean | null
  matched?: boolean
}

interface StockResult {
  ts_code: string
  code: string
  stock_name: string
  name?: string
  score: number
  signal: string
  trade_date: string
  date?: string
  reason_summary?: string | null
  evidence: ScreeningEvidenceItem[]
}

interface FilterMetadataItem {
  key: string
  label: string
  value_type: string
  operators: string[]
  description?: string
  param_schema?: Record<string, {
    type?: string
    required?: boolean
    min?: number
    max?: number
    default?: number | string | boolean
    enum?: string[]
  }>
  default_params?: Record<string, number | string | boolean>
  supported_adapters?: string[]
}

interface SavedScreenerPredicate {
  type: 'predicate'
  rule_key: string
  params: Record<string, unknown>
}

interface SavedScreenerDefinition {
  kind: 'saved_screener'
  ast_version: number
  registry_version: number
  scope?: Record<string, unknown>
  root: {
    type: 'group'
    op: 'all'
    children: SavedScreenerPredicate[]
  }
}

interface SavedSelectionCondition {
  id: number
  name: string
  category: string
  params: Record<string, any>
  definition?: SavedScreenerDefinition | null
}

interface AlertSubscriptionItem {
  id: number
  selection_condition_id: number
  name?: string | null
  status: 'active' | 'paused' | 'stale'
  last_run_trade_date?: string | null
}

const router = useRouter()
const loading = ref(false)
const hasResults = ref(false)
const hasRunOnce = ref(false)
const criteriaDirty = ref(false)
const formReady = ref(false)
const scanError = ref('')
const results = ref<StockResult[]>([])
const sortBy = ref('score')
const screeningMetadata = ref<{
  filter_fields?: FilterMetadataItem[]
  markets?: string[]
  registry_version?: number
} | null>(null)
const screeningSummary = ref({
  total: 0,
  tradeDate: '',
})
const criteriaPanelRef = ref<HTMLElement | null>(null)
const criteriaCollapsed = ref(false)
const myConditions = ref<SavedSelectionCondition[]>([])
const alertSubscriptions = ref<AlertSubscriptionItem[]>([])
const subscriptionBusyId = ref<number | null>(null)
const lastSubscriptionRunByCondition = reactive<Record<number, string>>({})
const templates = ref<Array<{ id: string; name: string; description: string; icon: string; filters: Record<string, any> }>>([])
const templatesLoading = ref(false)
const templatesCollapsed = ref(true)
const recentTemplates = ref<Array<{ id: string; name: string; icon: string; filters: Record<string, any> }>>([])
const savingStrategy = ref(false)
// Comparison mode state
const compareMode = ref(false)
const selectedHistoryIds = ref<Set<string>>(new Set())
const showCompareModal = ref(false)
const comparisonResults = ref<Array<{
  history_id: string
  trade_date: string | null
  total: number
  avg_score: number | null
  top_stocks: StockResult[]
}>>([])
const { trackFilterRun } = useAnalytics()
const CRITERIA_WIDTH_KEY = 'instock_selection_panel_width'
const CRITERIA_COLLAPSED_KEY = 'instock_selection_panel_collapsed'
const TEMPLATES_COLLAPSED_KEY = 'instock_templates_collapsed'
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')
const { panelWidth: criteriaPanelWidth, hydrateWidth: hydrateCriteriaWidth, startResize: startCriteriaResize } = useResizablePanel({
  panelRef: criteriaPanelRef,
  storageKey: CRITERIA_WIDTH_KEY,
  defaultWidth: 440,
  minWidth: 360,
  maxWidth: 640,
})

const criteria = reactive({
  priceMin: null as number | null,
  priceMax: null as number | null,
  market: '' as '' | 'sh' | 'sz',
  changeMin: null as number | null,
  changeMax: null as number | null,
  marketCapMin: null as number | null,
  marketCapMax: null as number | null,
  weekChangeMin: null as number | null,
  weekChangeMax: null as number | null,
  peMin: null as number | null,
  peMax: null as number | null,
  rsiMin: null as number | null,
  rsiMax: null as number | null,
  macdBullish: false,
  macdBearish: false,
  bollCloseAboveUpper: false,
  bollCloseBelowLower: false,
  pattern: '' as string,
  volumeRatioMin: null as number | null,
  volumeRatioMax: null as number | null,
})

const indicatorParams = reactive({
  rsiPeriod: 14,
  macdFastPeriod: 12,
  macdSlowPeriod: 26,
  macdSignalPeriod: 9,
  bollPeriod: 20,
  bollStddev: 2.0,
})

const canonicalFilterKeys = [
  'priceMin', 'priceMax',
  'changeMin', 'changeMax',
  'market',
  'rsiMin', 'rsiMax',
  'macdBullish', 'macdBearish',
  'bollCloseAboveUpper', 'bollCloseBelowLower',
  'pattern',
] as const
const defaultSupportedFilterLabels = ['价格范围', '日涨跌幅', '市场范围', 'RSI', 'MACD', 'BOLL', '形态']
const marketLabelMap: Record<string, string> = {
  sh: '沪市',
  sz: '深市',
}
const patternOptions = [
  { label: '锤子线', value: 'HAMMER' },
  { label: '倒锤子线', value: 'INVERTED_HAMMER' },
  { label: '十字星', value: 'DOJI' },
  { label: '看涨吞没', value: 'BULLISH_ENGULFING' },
  { label: '看跌吞没', value: 'BEARISH_ENGULFING' },
  { label: '看涨孕线', value: 'BULLISH_HARAMI' },
  { label: '看跌孕线', value: 'BEARISH_HARAMI' },
  { label: '头肩底', value: 'INVERSE_HEAD_SHOULDERS' },
  { label: '头肩顶', value: 'HEAD_SHOULDERS' },
  { label: '双底', value: 'DOUBLE_BOTTOM' },
  { label: '双顶', value: 'DOUBLE_TOP' },
  { label: 'MA 金叉', value: 'MA_GOLDEN_CROSS' },
  { label: 'MA 死叉', value: 'MA_DEATH_CROSS' },
]
const unavailableFilterGroups = [
  { title: '价格扩展', items: ['市值范围'] },
  { title: '涨跌扩展', items: ['周涨跌幅'] },
  { title: '技术指标扩展', items: ['市盈率', 'KDJ'] },
  { title: '成交量', items: ['量比'] },
]

const filterMetadataMap = computed(() => {
  const fields = screeningMetadata.value?.filter_fields || []
  return fields.reduce<Record<string, FilterMetadataItem>>((acc, item) => {
    acc[item.key] = item
    return acc
  }, {})
})

const marketOptions = computed(() => {
  const metadataMarkets = screeningMetadata.value?.markets || []
  const normalized = metadataMarkets
    .map((label) => {
      const value = Object.entries(marketLabelMap).find(([, name]) => name === label)?.[0]
      return value ? { value, label } : null
    })
    .filter((item): item is { value: 'sh' | 'sz'; label: string } => item !== null)

  return normalized.length > 0
    ? normalized
    : [
        { value: 'sh' as const, label: '沪市' },
        { value: 'sz' as const, label: '深市' },
    ]
})

const supportedFiltersDescription = computed(() => {
  const labels = screeningMetadata.value?.filter_fields?.length
    ? Array.from(
        new Set(
          screeningMetadata.value.filter_fields.map((item) => {
            if (item.key.startsWith('price')) return '价格范围'
            if (item.key.startsWith('change')) return '日涨跌幅'
            if (item.key === 'market') return '市场范围'
            if (item.key.startsWith('rsi')) return 'RSI'
            if (item.key.startsWith('macd')) return 'MACD'
            if (item.key.startsWith('boll')) return 'BOLL'
            if (item.key === 'pattern') return '形态'
            return item.label
          })
        )
      )
    : defaultSupportedFilterLabels

  return `当前启用：${labels.join('、')}。其他条件暂未接入。`
})

const activeFilterCount = computed(() => getEnabledFilterKeys().length)

const activeFilterSummary = computed(() => {
  if (activeFilterCount.value === 0) {
    return '未设置条件，将按默认全市场样本扫描。'
  }
  return `当前已设置 ${activeFilterCount.value} 个条件，点击开始筛选后生效。`
})

const scanStatusTitle = computed(() => {
  if (loading.value) return '正在扫描'
  if (scanError.value) return '执行筛选失败'
  if (criteriaDirty.value) return '条件已更新，尚未执行'
  if (hasRunOnce.value) return '已按当前条件完成扫描'
  return '等待开始筛选'
})

const scanStatusDescription = computed(() => {
  if (loading.value) return '正在按左侧条件计算结果，请稍候。'
  if (scanError.value) return scanError.value
  if (criteriaDirty.value) return `${activeFilterSummary.value} 修改不会自动扫描。`
  if (hasRunOnce.value) {
    const tradeDate = screeningSummary.value.tradeDate
      ? `交易日 ${formatDisplayDate(screeningSummary.value.tradeDate)}，`
      : ''
    return `${tradeDate}共 ${screeningSummary.value.total} 只结果。`
  }
  return activeFilterSummary.value
})

const emptyStateTitle = computed(() => {
  if (scanError.value) return '执行筛选失败'
  if (hasRunOnce.value) return '暂无匹配结果'
  return '先设置条件，再开始筛选'
})

const emptyStateDescription = computed(() => {
  if (scanError.value) return '本次扫描没有成功，页面已清空旧结果，避免误判。'
  if (hasRunOnce.value) return '当前筛选条件未命中任何股票，可以尝试：'
  return '选择模板或填写左侧条件后，点击“开始筛选”才会扫描全市场。'
})

const sortedResults = computed(() => {
  const sorted = [...results.value]
  sorted.sort((a, b) => {
    switch (sortBy.value) {
      case 'score': return Number(b.score) - Number(a.score)
      case 'date': return (b.date || b.trade_date || '').localeCompare(a.date || a.trade_date || '')
      default: return Number(b.score) - Number(a.score)
    }
  })
  return sorted
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

const totalPages = computed(() => Math.ceil(sortedResults.value.length / pageSize.value))

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return sortedResults.value.slice(start, end)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const delta = 2
  const pages: number[] = []
  for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
    pages.push(i)
  }
  return pages
})

// 重置分页当结果变化
watch(sortedResults, () => {
  currentPage.value = 1
})

const getTopBacktestStockCode = () => {
  const topStock = sortedResults.value.find((stock) => String(stock.code || '').trim())
  return String(topStock?.code || '').trim()
}

const formatDisplayDate = (value?: string | null) => {
  if (!value) return '-'
  if (value.includes('-')) return value
  if (value.length !== 8) return value
  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
}

const normalizeResult = (item: any): StockResult => ({
  ...item,
  code: item.code || item.symbol || item.ts_code?.split('.')[0],
  name: item.stock_name || item.name,
  evidence: Array.isArray(item.evidence) ? item.evidence : [],
})

const buildCanonicalFilters = () => {
  return canonicalFilterKeys.reduce<Record<string, unknown>>((acc, key) => {
    const value = criteria[key]
    if (typeof value === 'boolean') {
      if (value) {
        acc[key] = value
      }
      return acc
    }
    if (value !== null && value !== '') {
      acc[key] = value
    }
    return acc
  }, {})
}

const buildCanonicalScope = () => ({
  market: criteria.market || undefined,
  limit: 100,
})

const getParamBounds = (ruleKey: string, paramKey: string) => {
  const schema = filterMetadataMap.value[ruleKey]?.param_schema?.[paramKey]
  return {
    min: typeof schema?.min === 'number' ? schema.min : undefined,
    max: typeof schema?.max === 'number' ? schema.max : undefined,
  }
}

const getParamDefaultText = (ruleKey: string, paramKey: string, fallback: number | string) => {
  return String(filterMetadataMap.value[ruleKey]?.default_params?.[paramKey] ?? fallback)
}

const getMacdDefaultText = () => {
  return [
    getParamDefaultText('macdBullish', 'fast_period', 12),
    getParamDefaultText('macdBullish', 'slow_period', 26),
    getParamDefaultText('macdBullish', 'signal_period', 9),
  ].join('-')
}

const getBollDefaultText = () => {
  return `${getParamDefaultText('bollCloseAboveUpper', 'period', 20)}, ${getParamDefaultText('bollCloseAboveUpper', 'stddev', 2.0)}`
}

const syncIndicatorParamDefaults = () => {
  indicatorParams.rsiPeriod = Number(filterMetadataMap.value.rsiMin?.default_params?.period ?? 14)
  indicatorParams.macdFastPeriod = Number(filterMetadataMap.value.macdBullish?.default_params?.fast_period ?? 12)
  indicatorParams.macdSlowPeriod = Number(filterMetadataMap.value.macdBullish?.default_params?.slow_period ?? 26)
  indicatorParams.macdSignalPeriod = Number(filterMetadataMap.value.macdBullish?.default_params?.signal_period ?? 9)
  indicatorParams.bollPeriod = Number(filterMetadataMap.value.bollCloseAboveUpper?.default_params?.period ?? 20)
  indicatorParams.bollStddev = Number(filterMetadataMap.value.bollCloseAboveUpper?.default_params?.stddev ?? 2.0)
}

const getRuleDefaultParams = (ruleKey: string) => {
  const metadataDefaults = filterMetadataMap.value[ruleKey]?.default_params || {}
  if (ruleKey === 'rsiMin' || ruleKey === 'rsiMax') {
    return {
      ...metadataDefaults,
      period: indicatorParams.rsiPeriod,
    }
  }
  if (ruleKey === 'macdBullish' || ruleKey === 'macdBearish') {
    return {
      ...metadataDefaults,
      fast_period: indicatorParams.macdFastPeriod,
      slow_period: indicatorParams.macdSlowPeriod,
      signal_period: indicatorParams.macdSignalPeriod,
    }
  }
  if (ruleKey === 'bollCloseAboveUpper' || ruleKey === 'bollCloseBelowLower') {
    return {
      ...metadataDefaults,
      period: indicatorParams.bollPeriod,
      stddev: indicatorParams.bollStddev,
    }
  }
  return metadataDefaults
}

const buildCanonicalDefinition = (): SavedScreenerDefinition => {
  const children: SavedScreenerPredicate[] = []

  canonicalFilterKeys.forEach((key) => {
    if (key === 'market') return
    const value = criteria[key]
    if (value === undefined || value === null || value === '') return
    if (typeof value === 'boolean' && !value) return
    children.push({
      type: 'predicate',
      rule_key: key,
      params: {
        value,
        ...getRuleDefaultParams(key),
      },
    })
  })

  return {
    kind: 'saved_screener',
    ast_version: 1,
    registry_version: screeningMetadata.value?.registry_version || 1,
    scope: buildCanonicalScope(),
    root: {
      type: 'group',
      op: 'all',
      children,
    },
  }
}

const getEnabledFilterKeys = () => {
  return canonicalFilterKeys.filter((key) => {
    const value = criteria[key]
    if (typeof value === 'boolean') {
      return value
    }
    return value !== null && value !== ''
  })
}

const buildSelectionStrategyParams = () => {
  const selectionFilters = buildCanonicalFilters()
  const selectionDefinition = buildCanonicalDefinition()
  const selectionScope = buildCanonicalScope()

  return {
    source: 'selection',
    template_name: 'selection_bridge',
    selection_filters: selectionFilters,
    selection_scope: selectionScope,
    entry_rules: {
      mode: 'screening_match',
      inherits: ['selection_filters', 'selection_scope'],
      filters: selectionFilters,
      definition: selectionDefinition,
      scope: selectionScope,
    },
    exit_rules: {
      mode: 'configurable',
      rules: [
        { name: 'take_profit_pct', label: '止盈百分比', type: 'number' },
        { name: 'stop_loss_pct', label: '止损百分比', type: 'number' },
        { name: 'max_hold_days', label: '最大持有天数', type: 'number' },
      ],
    },
    backtest_config: {},
    strategy_params: {},
  }
}

const formatEvidence = (item: ScreeningEvidenceItem) => {
  const operator = item.operator ? ` ${item.operator} ${item.condition}` : ''
  const value = item.value ?? '-'
  return `${item.label}: ${value}${operator}`
}

const openStockDetail = (stock: StockResult) => {
  router.push({
    path: `/stock/${stock.code}`,
    query: {
      screening_date: stock.trade_date || stock.date || '',
    },
  })
}

const addToWatchlist = async (code: string) => {
  if (!code) return
  try {
    await attentionApi.add(code, 'watch')
    showNotification?.('success', `已加入关注: ${code}`)
  } catch (e) {
    console.error('Failed to add to watchlist:', e)
    showNotification?.('error', '加入关注失败')
  }
}

const fetchScreeningMetadata = async () => {
  try {
    const response = await selectionApi.getScreeningMetadata()
    screeningMetadata.value = response?.data || null
  } catch (e) {
    console.error('Failed to fetch screening metadata:', e)
    screeningMetadata.value = null
  } finally {
    syncIndicatorParamDefaults()
  }
}

const runSelection = async () => {
  if (validationErrorMessage.value) {
    showNotification?.('error', validationErrorMessage.value)
    return
  }

  loading.value = true
  scanError.value = ''
  try {
    const definition = buildCanonicalDefinition()
    const response = await selectionApi.runScreening({
      filters: buildCanonicalFilters(),
      definition: definition as unknown as Record<string, unknown>,
      scope: buildCanonicalScope(),
    })
    const payload = response?.data || {}
    results.value = (payload.items || []).map(normalizeResult)
    screeningSummary.value = {
      total: Number(payload.total || results.value.length),
      tradeDate: payload.query?.trade_date || results.value[0]?.trade_date || '',
    }
    hasResults.value = results.value.length > 0
    hasRunOnce.value = true
    criteriaDirty.value = false

    trackFilterRun({
      filterKeys: getEnabledFilterKeys(),
      market: criteria.market || null,
      resultCount: screeningSummary.value.total,
      tradeDate: screeningSummary.value.tradeDate || null,
    })

    showNotification?.('success', `筛选完成，共 ${results.value.length} 只`)
  } catch (e) {
    console.error('Failed to run selection:', e)
    results.value = []
    screeningSummary.value = { total: 0, tradeDate: '' }
    hasResults.value = false
    hasRunOnce.value = true
    criteriaDirty.value = false
    scanError.value = '接口返回失败或网络不可用，请稍后重试。'
    showNotification?.('error', '执行筛选失败')
  } finally {
    loading.value = false
  }
}

const fetchMyConditions = async () => {
  try {
    const conditions = await selectionApi.getMyConditions()
    myConditions.value = Array.isArray(conditions) ? conditions : []
  } catch (e) {
    myConditions.value = []
  }
}

const fetchAlertSubscriptions = async () => {
  try {
    const response = await alertSubscriptionApi.list()
    alertSubscriptions.value = Array.isArray(response?.data) ? response.data : []
  } catch (e) {
    alertSubscriptions.value = []
  }
}

const getSubscriptionForCondition = (conditionId: number) => {
  return alertSubscriptions.value.find((item) => item.selection_condition_id === conditionId)
}

const ensureSubscription = async (cond: SavedSelectionCondition) => {
  const existing = getSubscriptionForCondition(cond.id)
  if (existing && existing.status !== 'stale') {
    showNotification?.('info', '该筛选器已经订阅')
    return existing
  }

  subscriptionBusyId.value = cond.id
  try {
    const response = await alertSubscriptionApi.create({
      selection_condition_id: cond.id,
      name: cond.name,
      cooldown_trade_days: 1,
    })
    await fetchAlertSubscriptions()
    showNotification?.('success', '订阅已创建')
    return response?.data as AlertSubscriptionItem | undefined
  } catch (e) {
    console.error('Failed to create alert subscription:', e)
    showNotification?.('error', '创建订阅失败')
    return undefined
  } finally {
    subscriptionBusyId.value = null
  }
}

const triggerSubscription = async (cond: SavedSelectionCondition) => {
  const existing = getSubscriptionForCondition(cond.id) || await ensureSubscription(cond)
  if (!existing || existing.status === 'stale') return

  subscriptionBusyId.value = cond.id
  try {
    const response = await alertSubscriptionApi.run(existing.id)
    const run = response?.data?.run || {}
    const notification = response?.data?.notification
    const summary = run.summary || {}
    const text = notification
      ? `新增 ${Number(run.new_match_count || 0)} 只，已生成通知`
      : summary.notification_suppressed
        ? `新增 ${Number(run.new_match_count || 0)} 只，冷却中未通知`
        : `命中 ${Number(run.match_count || 0)} 只，无新增通知`
    lastSubscriptionRunByCondition[cond.id] = `${run.trade_date || ''} ${text}`.trim()
    await fetchAlertSubscriptions()
    showNotification?.('success', text)
  } catch (e: any) {
    console.error('Failed to trigger alert subscription:', e)
    const status = e?.response?.status
    if (status === 409) {
      await fetchAlertSubscriptions()
      showNotification?.('warning', '订阅已失效，请重新创建')
    } else {
      showNotification?.('error', '触发订阅失败')
    }
  } finally {
    subscriptionBusyId.value = null
  }
}

const fetchTemplates = async () => {
  templatesLoading.value = true
  try {
    const response = await selectionApi.getTemplates()
    templates.value = (response?.data || []).map((tpl: any) => ({
      ...tpl,
      filters: tpl.filters || {},
    }))
    const recentKey = 'selection_recent_templates'
    try {
      const stored = localStorage.getItem(recentKey)
      if (stored) {
        const recentIds = JSON.parse(stored) as string[]
        recentTemplates.value = templates.value.filter((tpl: any) => recentIds.includes(tpl.id))
      }
    } catch (e) {
      recentTemplates.value = []
    }
  } catch (e) {
    templates.value = []
    recentTemplates.value = []
  } finally {
    templatesLoading.value = false
  }
}

const applyTemplate = (tpl: { id: string; name: string; filters: Record<string, any> }) => {
  resetCriteria()
  Object.assign(criteria, tpl.filters)
  showNotification?.('info', `已应用模板：${tpl.name}`)
  const recentKey = 'selection_recent_templates'
  try {
    const stored = localStorage.getItem(recentKey)
    const recentIds: string[] = stored ? JSON.parse(stored) : []
    const filtered = recentIds.filter((id) => id !== tpl.id)
    const updated = [tpl.id, ...filtered].slice(0, 5)
    localStorage.setItem(recentKey, JSON.stringify(updated))
    const tplData = templates.value.find((t: any) => t.id === tpl.id)
    if (tplData && !recentTemplates.value.find((t: any) => t.id === tpl.id)) {
      recentTemplates.value = [tplData, ...recentTemplates.value].slice(0, 5)
    }
  } catch (e) {
    // ignore
  }
}

const applyDefinitionToForm = (definition?: SavedScreenerDefinition | null, params?: Record<string, any>) => {
  resetCriteria()
  if (params) {
    const canonical = canonicalFilterKeys.reduce<Record<string, any>>((acc, key) => {
      if (params[key] !== undefined) {
        acc[key] = params[key]
      }
      return acc
    }, {})
    Object.assign(criteria, canonical)
  }

  if (definition?.scope?.market && typeof definition.scope.market === 'string') {
    criteria.market = definition.scope.market as '' | 'sh' | 'sz'
  }

  const predicates = definition?.root?.children || []
  predicates.forEach((predicate) => {
    const ruleKey = predicate.rule_key as keyof typeof criteria
    const value = predicate.params?.value
    if (ruleKey in criteria && value !== undefined) {
      ;(criteria[ruleKey] as unknown) = value as never
    }
    if ((predicate.rule_key === 'rsiMin' || predicate.rule_key === 'rsiMax') && typeof predicate.params?.period === 'number') {
      indicatorParams.rsiPeriod = Number(predicate.params.period)
    }
    if (predicate.rule_key === 'macdBullish' || predicate.rule_key === 'macdBearish') {
      if (typeof predicate.params?.fast_period === 'number') indicatorParams.macdFastPeriod = Number(predicate.params.fast_period)
      if (typeof predicate.params?.slow_period === 'number') indicatorParams.macdSlowPeriod = Number(predicate.params.slow_period)
      if (typeof predicate.params?.signal_period === 'number') indicatorParams.macdSignalPeriod = Number(predicate.params.signal_period)
    }
    if (predicate.rule_key === 'bollCloseAboveUpper' || predicate.rule_key === 'bollCloseBelowLower') {
      if (typeof predicate.params?.period === 'number') indicatorParams.bollPeriod = Number(predicate.params.period)
      if (typeof predicate.params?.stddev === 'number') indicatorParams.bollStddev = Number(predicate.params.stddev)
    }
  })
}

const loadSavedCondition = (cond: SavedSelectionCondition) => {
  applyDefinitionToForm(cond.definition, cond.params)
  showNotification?.('info', `已加载条件：${cond.name}`)
}

const saveCriteria = async () => {
  const name = prompt("为筛选条件命名：", `自定义筛选 ${new Date().toLocaleDateString()}`)
  if (!name?.trim()) return
  if (validationErrorMessage.value) {
    showNotification?.('error', validationErrorMessage.value)
    return
  }

  try {
    await selectionApi.createCondition({
      name: name.trim(),
      category: "custom",
      description: "从筛选页面保存的条件",
      params: buildCanonicalFilters(),
      definition: buildCanonicalDefinition() as unknown as Record<string, unknown>,
      is_active: true,
    })
    showNotification?.('success', '筛选条件已保存')
    await fetchMyConditions()
    await fetchAlertSubscriptions()
  } catch (e) {
    showNotification?.('error', '保存失败')
  }
}

const saveAsStrategy = async (goToBacktest = false) => {
  const suggestedName = `筛选策略-${new Date().toLocaleDateString()}`
  const name = window.prompt('为策略命名：', suggestedName)
  if (!name?.trim()) return

  savingStrategy.value = true
  try {
    const created = await strategyApi.createMyStrategyFromSelection({
      name: name.trim(),
      description: '由筛选条件生成的策略模板',
      params: buildSelectionStrategyParams(),
      is_active: true,
    })
    const savedStrategyId = String(created?.id || '')
    if (goToBacktest && savedStrategyId) {
      const stockCode = getTopBacktestStockCode()
      if (!stockCode) {
        showNotification?.('warning', '当前没有可带入回测的股票结果，请先运行筛选')
        return
      }
      await router.push({
        path: '/backtest',
        query: {
          saved: savedStrategyId,
          stock: stockCode,
        },
      })
      showNotification?.('success', `策略已保存，已带着当前结果 Top1(${stockCode}) 进入回测页`)
      return
    }
    showNotification?.('success', '策略已保存，筛选到策略的桥接配置已建立')
  } catch (e) {
    console.error('Failed to save strategy from selection:', e)
    showNotification?.('error', '保存策略失败')
  } finally {
    savingStrategy.value = false
  }
}

const saveCurrentStrategy = () => {
  void saveAsStrategy(false)
}

const saveStrategyAndGoBacktest = () => {
  void saveAsStrategy(true)
}

// Comparison functionality
const extractSelectionId = (stock: any): string => {
  return stock.selection_id || stock.selectionId || ''
}

const enableCompareMode = () => {
  compareMode.value = true
  selectedHistoryIds.value = new Set()
}

const exitCompareMode = () => {
  compareMode.value = false
  selectedHistoryIds.value = new Set()
}

const toggleSelection = (selId: string) => {
  const newSet = new Set(selectedHistoryIds.value)
  if (newSet.has(selId)) {
    newSet.delete(selId)
  } else if (newSet.size < 4) {
    newSet.add(selId)
  }
  selectedHistoryIds.value = newSet
}

const toggleSelectAll = () => {
  const allIds = Array.from(new Set(results.value.map(extractSelectionId)))
  if (allCurrentSelectionIdsSelected.value) {
    selectedHistoryIds.value = new Set()
  } else {
    // Select up to 4
    selectedHistoryIds.value = new Set(allIds.slice(0, 4))
  }
}

const allCurrentSelectionIdsSelected = computed(() => {
  const uniqueIds = new Set(results.value.map(extractSelectionId))
  if (uniqueIds.size === 0) return false
  return uniqueIds.size > 0 && Array.from(uniqueIds).every(id => selectedHistoryIds.value.has(id))
})

const handleRowClick = (stock: any) => {
  const selId = extractSelectionId(stock)
  if (!selId) return
  toggleSelection(selId)
}

const startCompare = async () => {
  if (selectedHistoryIds.value.size < 2) return
  try {
    const response = await selectionApi.compareScreeningResults(Array.from(selectedHistoryIds.value))
    comparisonResults.value = (response?.data || []).map((item: any) => ({
      ...item,
      top_stocks: (item.top_stocks || []).map((s: any) => ({
        ...s,
        code: s.code || s.ts_code?.split('.')[0],
        name: s.stock_name,
      })),
    }))
    showCompareModal.value = true
  } catch (e) {
    console.error('Comparison failed:', e)
    showNotification?.('error', '对比失败')
  }
}

// 实时验证计算属性
const priceMinValid = computed(() => criteria.priceMin === null || criteria.priceMin === undefined || criteria.priceMin >= 0)
const priceMaxValid = computed(() => criteria.priceMax === null || criteria.priceMax === undefined || criteria.priceMax >= 0)
const priceMinInvalid = computed(() => !priceMinValid.value && criteria.priceMin !== null && criteria.priceMin !== undefined)
const priceMaxInvalid = computed(() => !priceMaxValid.value && criteria.priceMax !== null && criteria.priceMax !== undefined)
const priceRangeError = computed(() => {
  if (priceMinInvalid.value) return '最小价格不能为负数'
  if (priceMaxInvalid.value) return '最大价格不能为负数'
  if (criteria.priceMin != null && criteria.priceMax != null && criteria.priceMin > criteria.priceMax) {
    return '最小价格不能大于最大价格'
  }
  return ''
})

const changeMinValid = computed(() => criteria.changeMin === null || criteria.changeMin === undefined || (criteria.changeMin >= -100 && criteria.changeMin <= 100))
const changeMaxValid = computed(() => criteria.changeMax === null || criteria.changeMax === undefined || (criteria.changeMax >= -100 && criteria.changeMax <= 100))
const changeMinInvalid = computed(() => !changeMinValid.value && criteria.changeMin !== null && criteria.changeMin !== undefined)
const changeMaxInvalid = computed(() => !changeMaxValid.value && criteria.changeMax !== null && criteria.changeMax !== undefined)
const changeRangeError = computed(() => {
  if (changeMinInvalid.value) return '最小涨跌幅需在 -100% ~ +100% 范围内'
  if (changeMaxInvalid.value) return '最大涨跌幅需在 -100% ~ +100% 范围内'
  if (criteria.changeMin != null && criteria.changeMax != null && criteria.changeMin > criteria.changeMax) {
    return '最小涨跌幅不能大于最大涨跌幅'
  }
  return ''
})

// RSI 验证
const rsiMinValid = computed(() => criteria.rsiMin === null || criteria.rsiMin === undefined || (criteria.rsiMin >= 0 && criteria.rsiMin <= 100))
const rsiMaxValid = computed(() => criteria.rsiMax === null || criteria.rsiMax === undefined || (criteria.rsiMax >= 0 && criteria.rsiMax <= 100))
const rsiMinInvalid = computed(() => !rsiMinValid.value && criteria.rsiMin !== null && criteria.rsiMin !== undefined)
const rsiMaxInvalid = computed(() => !rsiMaxValid.value && criteria.rsiMax !== null && criteria.rsiMax !== undefined)
const rsiRangeError = computed(() => {
  if (rsiMinInvalid.value) return '最小 RSI 需在 0-100 范围内'
  if (rsiMaxInvalid.value) return '最大 RSI 需在 0-100 范围内'
  if (criteria.rsiMin != null && criteria.rsiMax != null && criteria.rsiMin > criteria.rsiMax) {
    return '最小 RSI 不能大于最大 RSI'
  }
  return ''
})

const rsiPeriodError = computed(() => {
  const { min, max } = getParamBounds('rsiMin', 'period')
  if (typeof min === 'number' && indicatorParams.rsiPeriod < min) return `RSI 周期需 >= ${min}`
  if (typeof max === 'number' && indicatorParams.rsiPeriod > max) return `RSI 周期需 <= ${max}`
  return ''
})

const macdParameterError = computed(() => {
  const fast = getParamBounds('macdBullish', 'fast_period')
  const slow = getParamBounds('macdBullish', 'slow_period')
  const signal = getParamBounds('macdBullish', 'signal_period')

  if (typeof fast.min === 'number' && indicatorParams.macdFastPeriod < fast.min) return `MACD 快线需 >= ${fast.min}`
  if (typeof fast.max === 'number' && indicatorParams.macdFastPeriod > fast.max) return `MACD 快线需 <= ${fast.max}`
  if (typeof slow.min === 'number' && indicatorParams.macdSlowPeriod < slow.min) return `MACD 慢线需 >= ${slow.min}`
  if (typeof slow.max === 'number' && indicatorParams.macdSlowPeriod > slow.max) return `MACD 慢线需 <= ${slow.max}`
  if (typeof signal.min === 'number' && indicatorParams.macdSignalPeriod < signal.min) return `MACD 信号需 >= ${signal.min}`
  if (typeof signal.max === 'number' && indicatorParams.macdSignalPeriod > signal.max) return `MACD 信号需 <= ${signal.max}`
  if (indicatorParams.macdFastPeriod >= indicatorParams.macdSlowPeriod) return 'MACD 快线必须小于慢线'
  return ''
})

const bollParameterError = computed(() => {
  const period = getParamBounds('bollCloseAboveUpper', 'period')
  const stddev = getParamBounds('bollCloseAboveUpper', 'stddev')

  if (typeof period.min === 'number' && indicatorParams.bollPeriod < period.min) return `BOLL 周期需 >= ${period.min}`
  if (typeof period.max === 'number' && indicatorParams.bollPeriod > period.max) return `BOLL 周期需 <= ${period.max}`
  if (typeof stddev.min === 'number' && indicatorParams.bollStddev < stddev.min) return `BOLL 标准差需 >= ${stddev.min}`
  if (typeof stddev.max === 'number' && indicatorParams.bollStddev > stddev.max) return `BOLL 标准差需 <= ${stddev.max}`
  return ''
})

const validationErrorMessage = computed(() => {
  return [
    priceRangeError.value,
    changeRangeError.value,
    rsiRangeError.value,
    rsiPeriodError.value,
    macdParameterError.value,
    bollParameterError.value,
  ].find(Boolean) || ''
})

const toggleCriteriaPanel = () => {
  criteriaCollapsed.value = !criteriaCollapsed.value
  window.localStorage.setItem(CRITERIA_COLLAPSED_KEY, criteriaCollapsed.value ? '1' : '0')
}

const setTemplatesCollapsed = (collapsed: boolean) => {
  templatesCollapsed.value = collapsed
  window.localStorage.setItem(TEMPLATES_COLLAPSED_KEY, collapsed ? '1' : '0')
}

const categoryClass = (category: string | null | undefined): string => {
  const c = String(category || '').toLowerCase()
  if (c.includes('price') || c.includes('价格')) return 'category-price'
  if (c.includes('change') || c.includes('涨跌')) return 'category-change'
  if (c.includes('macd')) return 'category-macd'
  if (c.includes('rsi')) return 'category-rsi'
  if (c.includes('pattern') || c.includes('形态')) return 'category-pattern'
  if (c.includes('fund') || c.includes('资金')) return 'category-fund'
  return 'category-default'
}

const resetCriteria = () => {
  criteria.priceMin = null
  criteria.priceMax = null
  criteria.market = ''
  criteria.changeMin = null
  criteria.changeMax = null
  criteria.marketCapMin = null
  criteria.marketCapMax = null
  criteria.weekChangeMin = null
  criteria.weekChangeMax = null
  criteria.peMin = null
  criteria.peMax = null
  criteria.rsiMin = null
  criteria.rsiMax = null
  criteria.macdBullish = false
  criteria.macdBearish = false
  criteria.bollCloseAboveUpper = false
  criteria.bollCloseBelowLower = false
  criteria.pattern = ''
  criteria.volumeRatioMin = null
  criteria.volumeRatioMax = null
  syncIndicatorParamDefaults()
}

watch([criteria, indicatorParams], () => {
  if (formReady.value) {
    scanError.value = ''
    criteriaDirty.value = true
  }
}, { deep: true })

onMounted(async () => {
  await Promise.all([
    fetchMyConditions(),
    fetchAlertSubscriptions(),
    fetchScreeningMetadata(),
    fetchTemplates(),
  ])
  hydrateCriteriaWidth()
  criteriaCollapsed.value = window.localStorage.getItem(CRITERIA_COLLAPSED_KEY) === '1'
  const storedTemplateState = window.localStorage.getItem(TEMPLATES_COLLAPSED_KEY)
  templatesCollapsed.value = storedTemplateState === null ? true : storedTemplateState === '1'
  formReady.value = true
})

</script>

<style scoped lang="scss">
.selection-page {
  padding: 24px;
  min-height: 100%;
  background:
    radial-gradient(circle at top left, rgba(41, 98, 255, 0.12), transparent 34rem),
    radial-gradient(circle at top right, rgba(0, 200, 83, 0.08), transparent 28rem),
    #0d0d0d;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;

  .eyebrow {
    display: inline-flex;
    margin-bottom: 8px;
    padding: 4px 10px;
    border: 1px solid rgba(41, 98, 255, 0.28);
    border-radius: 999px;
    background: rgba(41, 98, 255, 0.08);
    color: #9ab7ff;
    font-size: 12px;
    letter-spacing: 0.04em;
  }

  h1 {
    margin: 0;
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.02em;
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.header-right {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
  max-width: 560px;
}

.secondary-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;

  &.btn-primary {
    background: #2962FF;
    color: white;

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  &.btn-secondary {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);
  }

  &.btn-quiet {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.58);
  }

  &.btn-hero {
    padding: 12px 22px;
    box-shadow: 0 12px 30px rgba(41, 98, 255, 0.26);
  }

  &.btn-small {
    padding: 6px 12px;
    font-size: 12px;
  }
}

.workflow-guide {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.workflow-step {
  display: flex;
  gap: 12px;
  min-width: 0;
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  background: rgba(26, 26, 26, 0.54);

  &.active {
    border-color: rgba(41, 98, 255, 0.28);
    background: rgba(41, 98, 255, 0.08);
  }

  strong {
    display: block;
    margin-bottom: 4px;
    color: rgba(255, 255, 255, 0.88);
    font-size: 13px;
  }

  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.52);
    font-size: 12px;
    line-height: 1.45;
  }
}

.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.86);
  font-size: 13px;
  font-weight: 700;
}

.selection-layout {
  display: flex;
  gap: 12px;
}

.criteria-panel {
  min-width: 360px;
  max-width: 640px;
  flex-shrink: 0;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  max-height: calc(100vh - 140px);
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

.start-section {
  padding: 16px;
  border: 1px solid rgba(41, 98, 255, 0.18);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(41, 98, 255, 0.12), rgba(255, 255, 255, 0.03));
}

.effect-note,
.default-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.18);
  font-size: 12px;

  span {
    color: rgba(255, 255, 255, 0.48);
  }

  strong {
    color: rgba(255, 255, 255, 0.84);
    text-align: right;
  }
}

.default-note {
  margin-top: 8px;
}

.panel-resizer {
  position: relative;
  flex: 0 0 12px;
  margin: 0 -6px;
  cursor: col-resize;
  touch-action: none;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
  }

  &::after {
    content: '';
    position: absolute;
    top: 16px;
    bottom: 16px;
    left: 50%;
    width: 2px;
    transform: translateX(-50%);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
    transition: background 0.2s ease;
  }

  &:hover::after {
    background: rgba(41, 98, 255, 0.75);
  }
}

.panel-section {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }

  h3 {
    margin: 0 0 16px;
    font-size: 14px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
  }
}

.utility-section {
  padding-top: 4px;
}

.templates-section {
  background: rgba(41, 98, 255, 0.06);
  border: 1px solid rgba(41, 98, 255, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;

  .templates-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-bottom: 12px;
  }

  .template-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(41, 98, 255, 0.15);
      border-color: rgba(41, 98, 255, 0.35);
    }

    .template-icon {
      font-size: 20px;
      margin-bottom: 2px;
    }

    .template-name {
      font-size: 13px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
    }

    .template-desc {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      line-height: 1.4;
    }
  }

  .templates-loading {
    text-align: center;
    padding: 24px;
    color: rgba(255, 255, 255, 0.5);
    font-size: 13px;
  }

  .templates-toggle {
    width: 100%;
    padding: 8px;
    background: transparent;
    border: 1px dashed rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    color: rgba(255, 255, 255, 0.5);
    font-size: 12px;
    cursor: pointer;

    &:hover {
      background: rgba(255, 255, 255, 0.05);
      border-color: rgba(255, 255, 255, 0.3);
    }
  }
}

.templates-collapsed-bar {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(41, 98, 255, 0.06);
  border: 1px solid rgba(41, 98, 255, 0.15);
  border-radius: 12px;
  text-align: center;
}

.recent-templates-section {
  background: rgba(255, 152, 0, 0.06);
  border: 1px solid rgba(255, 152, 0, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;

  .recent-templates-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  h4 {
    margin: 0 0 10px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.58);
  }

  .recent-template-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);

    &:hover {
      background: rgba(255, 152, 0, 0.12);
      border-color: rgba(255, 152, 0, 0.3);
    }
  }
}

.compact-heading {
  margin-top: 16px;

  h4 {
    margin: 0 0 6px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.76);
  }
}

.section-heading {
  margin-bottom: 16px;

  h3 {
    margin-bottom: 6px;
  }

  p {
    margin: 0;
    font-size: 12px;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.5);
  }
}

.saved-conditions-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.saved-condition-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: background 0.2s, border-color 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.12);
  }

  .saved-condition-main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex: 1 1 160px;
    min-width: 0;
    padding: 0;
    border: 0;
    background: transparent;
    cursor: pointer;
    text-align: left;

    .saved-condition-name {
      overflow: hidden;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.9);
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }

  .saved-condition-category {
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 500;

    &.category-price { background: rgba(41, 98, 255, 0.15); color: #7aa7ff; border: 1px solid rgba(41, 98, 255, 0.3); }
    &.category-change { background: rgba(255, 152, 0, 0.15); color: #FFB74D; border: 1px solid rgba(255, 152, 0, 0.3); }
    &.category-macd { background: rgba(139, 195, 74, 0.15); color: #AED581; border: 1px solid rgba(139, 195, 74, 0.3); }
    &.category-rsi { background: rgba(233, 30, 99, 0.15); color: #F06292; border: 1px solid rgba(233, 30, 99, 0.3); }
    &.category-pattern { background: rgba(156, 39, 176, 0.15); color: #BA68C8; border: 1px solid rgba(156, 39, 176, 0.3); }
    &.category-fund { background: rgba(0, 188, 212, 0.15); color: #4DD0E1; border: 1px solid rgba(0, 188, 212, 0.3); }
    &.category-default { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.6); border: 1px solid rgba(255, 255, 255, 0.2); }
  }
}

.saved-condition-actions {
  display: flex;
  gap: 6px;
  margin-left: 8px;
}

.subscription-note {
  flex: 0 0 100%;
  margin-top: 8px;
  font-size: 11px;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.5);

  &.warning {
    color: #FFB74D;
  }
}

.criteria-group {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }

  label {
    display: block;
    margin-bottom: 8px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.criteria-select {
  width: 100%;
}

.range-inputs {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
}

.param-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;

  &.single-column {
    grid-template-columns: minmax(0, 1fr);
  }
}

.param-field {
  display: flex;
  flex-direction: column;
  gap: 6px;

  span {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.56);
  }
}

.input-small {
  min-width: 0;
  width: 100%;
  padding: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }

  &.invalid {
    border-color: #ff5252;
    background: rgba(255, 82, 82, 0.08);
  }

  &.valid {
    border-color: #4CAF50;
    background: rgba(76, 175, 80, 0.08);
  }
}

.criteria-hint {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  margin-top: 4px;

  &.error {
    color: #ff5252;
  }
}

.legacy-grid {
  display: grid;
  gap: 12px;
}

.legacy-card {
  padding: 14px;
  border: 1px dashed rgba(255, 255, 255, 0.14);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);

  h4 {
    margin: 0 0 10px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.72);
  }
}

.legacy-list {
  margin: 0;
  padding-left: 18px;
  color: rgba(255, 255, 255, 0.48);
  font-size: 12px;
  line-height: 1.6;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.76);

  input {
    accent-color: #2962FF;
  }
}

.field-hint {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.48);
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  min-width: 0;

  input {
    accent-color: #2962FF;
  }

  span {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
    overflow-wrap: anywhere;
  }
}

.results-panel {
  flex: 1;
  min-width: 0;
}

.scan-status-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
  padding: 18px 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background: rgba(26, 26, 26, 0.72);

  &.dirty {
    border-color: rgba(255, 183, 77, 0.3);
    background: rgba(255, 183, 77, 0.08);
  }

  &.complete {
    border-color: rgba(105, 240, 174, 0.26);
    background: rgba(0, 200, 83, 0.08);
  }

  &.error {
    border-color: rgba(255, 82, 82, 0.32);
    background: rgba(255, 82, 82, 0.08);
  }

  strong {
    display: block;
    margin-bottom: 5px;
    color: rgba(255, 255, 255, 0.9);
    font-size: 16px;
  }

  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.56);
    font-size: 13px;
    line-height: 1.45;
  }
}

.availability-note {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px 14px;
  background: rgba(41, 98, 255, 0.08);
  border: 1px solid rgba(41, 98, 255, 0.2);
  border-radius: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.72);

  strong {
    color: #9ab7ff;
  }
}

@media (max-width: 1200px) {
  .selection-layout {
    flex-direction: column;
    gap: 24px;
  }

  .criteria-panel {
    width: 100%;
    min-width: 0;
    max-width: none;
    max-height: 50vh;
  }

  .workflow-guide {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }

  .header-right,
  .secondary-actions {
    justify-content: flex-start;
    max-width: none;
  }

  .panel-resizer {
    display: none;
  }
}

@media (max-width: 720px) {
  .selection-page {
    padding: 16px;
  }

  .scan-status-card {
    align-items: stretch;
    flex-direction: column;
  }

  .range-inputs,
  .param-grid {
    grid-template-columns: 1fr;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  text-align: center;

  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  h3 {
    margin: 0 0 8px;
    font-size: 20px;
  }

  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.5);
  }

  .empty-suggestions {
    margin: 16px 0 24px;
    padding: 0;
    list-style: none;
    text-align: left;
    color: rgba(255, 255, 255, 0.45);
    font-size: 13px;
    line-height: 1.6;

    li {
      margin-bottom: 4px;
      padding-left: 16px;
      position: relative;

      &::before {
        content: "•";
        position: absolute;
        left: 0;
        color: rgba(255, 255, 255, 0.3);
      }
    }
  }
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.results-count {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.results-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.results-date {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
}

.results-actions {
  display: flex;
  gap: 12px;
}

.results-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;

  .pagination-info {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .pagination-btn {
    padding: 4px 12px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    background: transparent;
    color: rgba(255, 255, 255, 0.6);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      color: rgba(255, 255, 255, 0.9);
      border-color: rgba(255, 255, 255, 0.24);
    }

    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  }

  .pagination-pages {
    display: flex;
    gap: 4px;
  }

  .pagination-page {
    min-width: 28px;
    padding: 4px 8px;
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
    color: rgba(255, 255, 255, 0.6);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.06);
    }

    &.active {
      background: rgba(41, 98, 255, 0.16);
      color: #6ab0ff;
      border-color: rgba(41, 98, 255, 0.35);
    }
  }
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(26, 26, 26, 0.5);
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

.results-table-wrapper {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.results-table {
  width: 100%;
  border-collapse: collapse;

  th,
  td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }

  th {
    background: rgba(26, 26, 26, 0.95);
    font-size: 12px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
  }

  td {
    font-size: 13px;
  }

  tbody tr {
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.03);
    }
  }
}

.stock-code {
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.stock-name {
  color: rgba(255, 255, 255, 0.7);
}

.reason-cell {
  min-width: 280px;
}

.reason-summary {
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.84);
  line-height: 1.4;
}

.evidence-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.evidence-chip {
  display: inline-flex;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.58);
  font-size: 11px;
}

.detail-link {
  padding: 6px 10px;
  border: 1px solid rgba(41, 98, 255, 0.35);
  border-radius: 999px;
  background: rgba(41, 98, 255, 0.1);
  color: #9ab7ff;
  font-size: 12px;
  cursor: pointer;
  margin-right: 6px;
}

.watchlist-link {
  padding: 6px 10px;
  border: 1px solid rgba(0, 200, 83, 0.35);
  border-radius: 999px;
  background: rgba(0, 200, 83, 0.1);
  color: #69F0AE;
  font-size: 12px;
  cursor: pointer;

  &:hover {
    background: rgba(0, 200, 83, 0.2);
  }
}

.macd-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;

  &.bullish {
    background: rgba(0, 200, 83, 0.15);
    color: #00C853;
  }

  &.bearish {
    background: rgba(255, 23, 68, 0.15);
    color: #FF1744;
  }
}

// Comparison modal styles
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.modal-content {
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  max-width: 1200px;
  width: 100%;
  max-height: 90vh;
  overflow: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 28px;
    color: rgba(255, 255, 255, 0.5);
    cursor: pointer;
    line-height: 1;

    &:hover {
      color: rgba(255, 255, 255, 0.9);
    }
  }
}

.modal-body {
  padding: 24px;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.comparison-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
}

.card-header {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  .card-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .card-subtitle {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.card-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;

  .stat {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .stat-label {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.5);
    }

    .stat-value {
      font-size: 20px;
      font-weight: 600;
      color: #2962FF;
    }
  }
}

.card-top-stocks {
  h4 {
    margin: 0 0 10px;
    font-size: 13px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  li {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 8px;

    .stock-code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 600;
      color: rgba(255, 255, 255, 0.9);
    }

    .stock-name {
      flex: 1;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.7);
    }

    .stock-score {
      font-size: 13px;
      font-weight: 600;
      color: #9ab7ff;
    }
  }
}

// Row selection style
.row-selected {
  background: rgba(41, 98, 255, 0.12) !important;
}

.results-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

</style>
