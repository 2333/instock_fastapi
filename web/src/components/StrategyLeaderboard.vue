<template>
  <div class="strategy-leaderboard">
    <div class="leaderboard-header">
      <h3>{{ title }}</h3>
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="tab-btn"
          :class="{ active: activeTab === tab.value }"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="leaderboard-list">
      <div
        v-for="(strategy, index) in displayedStrategies"
        :key="strategy.id"
        class="leaderboard-item"
        :class="getRankClass(index)"
        @click="openStrategy(strategy)"
      >
        <div class="rank">{{ index + 1 }}</div>
        <div class="strategy-info">
          <div class="strategy-name">{{ strategy.name }}</div>
          <div class="strategy-meta">
            <span class="rating">★ {{ strategy.rating.toFixed(1) }}</span>
            <span class="favorites">❤️ {{ strategy.favorite_count }}</span>
            <span v-if="strategy.backtest_count" class="backtests">📊 {{ strategy.backtest_count }}</span>
          </div>
        </div>
        <div class="strategy-action">
          <button class="btn btn-sm" @click.stop="copyStrategy(strategy)">复制</button>
        </div>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-if="error" class="error-state">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { strategySocialApi } from '@/api'

const router = useRouter()

interface Strategy {
  id: number
  name: string
  rating: number
  favorite_count: number
  backtest_count?: number
  comment_count?: number
  is_official?: boolean
  risk_level?: string
}

interface Props {
  title?: string
  initialTab?: string
  limit?: number
}

const props = withDefaults(defineProps<Props>(), {
  title: '策略排行榜',
  initialTab: 'rating',
  limit: 20,
})

const emit = defineEmits<{
  (e: 'strategy-click', strategy: Strategy): void
}>()

const activeTab = ref(props.initialTab)
const strategies = ref<Strategy[]>([])
const loading = ref(false)
const error = ref('')

const tabs = [
  { label: '总榜', value: 'rating' },
  { label: '热门', value: 'favorite' },
  { label: '高收益', value: 'backtest' },
  { label: '低回撤', value: 'drawdown' },
]

const displayedStrategies = computed(() => strategies.value.slice(0, props.limit))

function getRankClass(index: number): string {
  if (index === 0) return 'rank-1'
  if (index === 1) return 'rank-2'
  if (index === 2) return 'rank-3'
  return ''
}

async function loadStrategies() {
  loading.value = true
  error.value = ''
  try {
    const sortMap: Record<string, string> = {
      rating: 'rating',
      favorite: 'favorite_count',
      backtest: 'backtest_count',
      drawdown: 'max_drawdown', // 假设后端支持
    }
    const res = await strategySocialApi.listPublic({
      sort_by: sortMap[activeTab.value] || 'rating',
      limit: props.limit,
    })
    strategies.value = (res.data?.items || []).map((s: any) => ({
      id: s.id,
      name: s.name,
      rating: s.rating || 0,
      favorite_count: s.favorite_count || 0,
      backtest_count: s.backtest_count || 0,
      comment_count: s.comment_count || 0,
      is_official: s.is_official,
      risk_level: s.risk_level,
    }))
  } catch (e) {
    console.error('Failed to load leaderboard:', e)
    error.value = '加载失败'
  } finally {
    loading.value = false
  }
}

function openStrategy(strategy: Strategy) {
  emit('strategy-click', strategy)
}

function copyStrategy(strategy: Strategy) {
  router.push({
    path: '/backtest',
    query: { strategy: strategy.name },
  })
}

watch(activeTab, () => {
  loadStrategies()
})

onMounted(() => {
  loadStrategies()
})
</script>

<style scoped lang="scss">
.strategy-leaderboard {
  background: var(--color-bg-secondary);
  border-radius: 12px;
  padding: 16px;
}

.leaderboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    font-size: 16px;
  }

  .tabs {
    display: flex;
    gap: 4px;

    .tab-btn {
      background: none;
      border: none;
      padding: 6px 12px;
      font-size: 12px;
      cursor: pointer;
      border-radius: 4px;
      color: var(--color-text-secondary);
      transition: all 0.2s;

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

.leaderboard-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.leaderboard-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--color-bg-tertiary);
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: var(--color-border);
  }

  .rank {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--color-text-tertiary);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    flex-shrink: 0;
  }

  &.rank-1 .rank {
    background: #ffc107;
    color: #000;
  }
  &.rank-2 .rank {
    background: #9e9e9e;
  }
  &.rank-3 .rank {
    background: #cd7f32;
  }

  .strategy-info {
    flex: 1;
    min-width: 0;

    .strategy-name {
      margin: 0 0 4px;
      font-size: 14px;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .strategy-meta {
      display: flex;
      gap: 12px;
      font-size: 11px;
      color: var(--color-text-secondary);

      .rating {
        color: #ffc107;
      }
    }
  }

  .strategy-action {
    flex-shrink: 0;

    .btn-sm {
      padding: 4px 10px;
      font-size: 11px;
    }
  }
}

.loading-state,
.error-state {
  text-align: center;
  padding: 24px;
  color: var(--color-text-secondary);
}
</style>
