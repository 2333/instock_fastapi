<template>
  <div class="strategy-market-page">
    <div class="page-header">
      <div class="header-left">
        <h1>策略市场</h1>
        <p class="subtitle">发现和分享优质策略模板</p>
      </div>
      <div class="header-right">
        <button class="btn btn-primary" @click="openCreateStrategy">+ 创建策略</button>
      </div>
    </div>

    <div class="market-content">
      <!-- 侧边栏筛选 -->
      <aside class="filters-sidebar">
        <div class="filter-section">
          <h4>策略类型</h4>
          <div class="filter-options">
            <label v-for="type in strategyTypes" :key="type.value" class="checkbox-label">
              <input
                type="checkbox"
                :value="type.value"
                v-model="filters.strategy_type"
              />
              <span>{{ type.label }}</span>
            </label>
          </div>
        </div>

        <div class="filter-section">
          <h4>风险等级</h4>
          <div class="filter-options">
            <label v-for="level in riskLevels" :key="level.value" class="checkbox-label">
              <input
                type="checkbox"
                :value="level.value"
                v-model="filters.risk_level"
              />
              <span>{{ level.label }}</span>
            </label>
          </div>
        </div>

        <div class="filter-section">
          <h4>排序方式</h4>
          <div class="sort-options">
            <button
              v-for="sort in sortOptions"
              :key="sort.value"
              class="sort-btn"
              :class="{ active: sortBy === sort.value }"
              @click="sortBy = sort.value"
            >
              {{ sort.label }}
            </button>
          </div>
        </div>

        <button class="clear-filters-btn" @click="clearFilters">清除筛选</button>
      </aside>

      <!-- 策略列表 -->
      <main class="strategies-main">
        <div class="search-bar">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索策略名称..."
            class="search-input"
          />
        </div>

        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else-if="error" class="error-state">{{ error }}</div>
        <div v-else-if="strategies.length === 0" class="empty-state">
          <p>暂无符合条件的策略</p>
        </div>
        <div v-else class="strategies-grid">
          <StrategyCard
            v-for="strategy in strategies"
            :key="strategy.id"
            :strategy="strategy"
            @favorite-toggle="onFavoriteToggle"
            @rate="onRate"
          />
        </div>

        <!-- 分页 -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            class="page-btn"
            :disabled="currentPage === 1"
            @click="currentPage--"
          >
            上一页
          </button>
          <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
          <button
            class="page-btn"
            :disabled="currentPage === totalPages"
            @click="currentPage++"
          >
            下一页
          </button>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import StrategyCard from '@/components/StrategyCard.vue'
import { strategySocialApi } from '@/api'

const router = useRouter()

interface Strategy {
  id: number
  name: string
  description?: string
  rating: number
  rating_count: number
  favorite_count: number
  comment_count: number
  backtest_count: number
  is_public: boolean
  is_official: boolean
  tags?: string[]
  risk_level?: string
  suitable_market?: string
}

const strategyTypes = [
  { label: 'MA 交叉', value: 'ma_crossover' },
  { label: 'RSI 超卖', value: 'rsi_oversold' },
  { label: 'MACD', value: 'macd' },
  { label: '布林带', value: 'bollinger' },
  { label: '买持有', value: 'buy_hold' },
]

const riskLevels = [
  { label: '低风险', value: 'low' },
  { label: '中风险', value: 'medium' },
  { label: '高风险', value: 'high' },
]

const sortOptions = [
  { label: '综合评分', value: 'rating' },
  { label: '收藏最多', value: 'favorite' },
  { label: '回测最多', value: 'backtest' },
]

const filters = ref({
  strategy_type: [] as string[],
  risk_level: [] as string[],
  tags: [] as string[],
})

const searchQuery = ref('')
const sortBy = ref('rating')
const currentPage = ref(1)
const pageSize = 20

const strategies = ref<Strategy[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')

const totalPages = computed(() => Math.ceil(total.value / pageSize))

async function loadStrategies() {
  loading.value = true
  error.value = ''
  try {
    const params: any = {
      sort_by: sortBy.value,
      limit: pageSize,
      offset: (currentPage.value - 1) * pageSize,
    }

    if (filters.value.strategy_type.length) {
      params.strategy_type = filters.value.strategy_type.join(',')
    }
    if (filters.value.risk_level.length) {
      params.risk_level = filters.value.risk_level.join(',')
    }
    if (searchQuery.value) {
      // 假设后端支持 name 模糊查询（当前未实现，前端过滤）
    }

    const res = await strategySocialApi.listPublic(params)
    strategies.value = (res.data?.items || []).map((s: any) => ({
      id: s.id,
      name: s.name,
      description: s.description,
      rating: s.rating || 0,
      rating_count: s.rating_count || 0,
      favorite_count: s.favorite_count || 0,
      comment_count: s.comment_count || 0,
      backtest_count: s.backtest_count || 0,
      is_public: s.is_public,
      is_official: s.is_official,
      tags: s.tags,
      risk_level: s.risk_level,
      suitable_market: s.suitable_market,
    }))
    total.value = res.data?.total || strategies.value.length
  } catch (e) {
    console.error('Failed to load strategies:', e)
    error.value = '加载失败'
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  filters.value = {
    strategy_type: [],
    risk_level: [],
    tags: [],
  }
  searchQuery.value = ''
  sortBy.value = 'rating'
  currentPage.value = 1
  loadStrategies()
}

function onFavoriteToggle(strategyId: number, favorited: boolean) {
  // 更新本地策略状态
  const strategy = strategies.value.find(s => s.id === strategyId)
  if (strategy) {
    strategy.favorite_count += favorited ? 1 : -1
  }
}

function onRate(strategyId: number, rating: number) {
  // 更新本地策略评分
  const strategy = strategies.value.find(s => s.id === strategyId)
  if (strategy) {
    strategy.rating = rating
    // 评分人数也会变化，但这里简化处理
  }
}

function openCreateStrategy() {
  router.push('/backtest')
}

watch([sortBy, currentPage, filters, searchQuery], () => {
  loadStrategies()
})

onMounted(() => {
  loadStrategies()
})
</script>

<style scoped lang="scss">
.strategy-market-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;

  .header-left {
    h1 {
      margin: 0 0 4px;
      font-size: 24px;
    }

    .subtitle {
      margin: 0;
      color: var(--color-text-secondary);
    }
  }
}

.market-content {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 24px;
}

.filters-sidebar {
  background: var(--color-bg-secondary);
  border-radius: 8px;
  padding: 16px;
  height: fit-content;
  position: sticky;
  top: 24px;

  .filter-section {
    margin-bottom: 20px;

    h4 {
      margin: 0 0 8px;
      font-size: 14px;
      color: var(--color-text-secondary);
    }

    .filter-options {
      display: flex;
      flex-direction: column;
      gap: 6px;

      .checkbox-label {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        cursor: pointer;

        input[type="checkbox"] {
          width: 16px;
          height: 16px;
        }
      }
    }

    .sort-options {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .sort-btn {
        background: none;
        border: none;
        text-align: left;
        padding: 6px 8px;
        font-size: 13px;
        cursor: pointer;
        border-radius: 4px;
        color: var(--color-text);

        &.active {
          background: var(--color-primary);
          color: white;
        }

        &:hover:not(.active) {
          background: var(--color-bg-tertiary);
        }
      }
    }
  }

  .clear-filters-btn {
    width: 100%;
    padding: 8px;
    background: none;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
    color: var(--color-text-secondary);

    &:hover {
      background: var(--color-bg-tertiary);
    }
  }
}

.strategies-main {
  .search-bar {
    margin-bottom: 16px;

    .search-input {
      width: 100%;
      max-width: 400px;
      padding: 10px 16px;
      border: 1px solid var(--color-border);
      border-radius: 8px;
      font-size: 14px;

      &:focus {
        outline: none;
        border-color: var(--color-primary);
      }
    }
  }

  .strategies-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }

  .loading-state,
  .error-state,
  .empty-state {
    text-align: center;
    padding: 60px 0;
    color: var(--color-text-secondary);
  }

  .pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    margin-top: 24px;
    padding: 16px 0;

    .page-btn {
      padding: 8px 16px;
      border: 1px solid var(--color-border);
      border-radius: 6px;
      background: var(--color-bg-primary);
      cursor: pointer;

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      &:not(:disabled):hover {
        background: var(--color-bg-secondary);
      }
    }

    .page-info {
      font-size: 13px;
      color: var(--color-text-secondary);
    }
  }
}
</style>
