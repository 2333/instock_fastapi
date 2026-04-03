<template>
  <div class="strategy-card" :class="{ 'is-official': strategy.is_official }">
    <div class="card-header">
      <div class="strategy-info">
        <h3 class="strategy-name">{{ strategy.name }}</h3>
        <p class="strategy-desc" v-if="strategy.description">{{ strategy.description }}</p>
      </div>
      <div class="strategy-badges">
        <span v-if="strategy.is_official" class="badge official">官方</span>
        <span v-if="strategy.risk_level" class="badge risk" :class="strategy.risk_level">
          {{ riskLabel }}
        </span>
      </div>
    </div>

    <div class="card-stats">
      <div class="stat-item">
        <span class="stat-label">评分</span>
        <div class="rating-stars">
          <span v-for="n in 5" :key="n" class="star" :class="{ filled: n <= Math.round(strategy.rating) }">
            {{ n <= Math.round(strategy.rating) ? '★' : '☆' }}
          </span>
          <span class="rating-value">{{ strategy.rating.toFixed(1) }}</span>
        </div>
        <span class="stat-count">({{ strategy.rating_count }})</span>
      </div>

      <div class="stat-item">
        <span class="stat-label">收藏</span>
        <span class="stat-value">{{ strategy.favorite_count }}</span>
      </div>

      <div class="stat-item">
        <span class="stat-label">评论</span>
        <span class="stat-value">{{ strategy.comment_count }}</span>
      </div>

      <div class="stat-item">
        <span class="stat-label">回测</span>
        <span class="stat-value">{{ strategy.backtest_count }}</span>
      </div>
    </div>

    <div v-if="strategy.tags && strategy.tags.length" class="card-tags">
      <span v-for="tag in strategy.tags" :key="tag" class="tag">{{ tag }}</span>
    </div>

    <div class="card-actions">
      <button class="btn btn-secondary btn-small" @click="openDetails">查看详情</button>
      <button class="btn btn-primary btn-small" @click="copyToMyStrategy">复制并回测</button>
      <button class="btn-icon" @click="toggleFavorite" :class="{ favorited: userFavorited }" title="收藏">
        {{ userFavorited ? '❤️' : '🤍' }}
      </button>
    </div>

    <!-- 详情弹窗 -->
    <StrategyDetailModal
      v-if="showModal"
      :strategy="strategy"
      :user-rating="userRating"
      :user-favorited="userFavorited"
      @close="closeModal"
      @rate="handleRate"
      @favorite="handleFavorite"
      @comment="handleComment"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { strategySocialApi } from '@/api'

const router = useRouter()

interface Props {
  strategy: {
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
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'favorite-toggle', strategyId: number, favorited: boolean): void
  (e: 'rate', strategyId: number, rating: number): void
}>()

const showModal = ref(false)
const userRating = ref<number | null>(null)
const userFavorited = ref(false)

const riskLabel = computed(() => {
  const labels: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
  }
  return labels[props.strategy.risk_level || ''] || props.strategy.risk_level || ''
})

onMounted(async () => {
  // 获取用户对当前策略的状态（已登录时）
  // 简化：暂不查询，点击操作时再处理
})

function openDetails() {
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function copyToMyStrategy() {
  // 复制策略到个人模板（需调用策略 API）
  // 简化演示：跳转到回测页面并预填策略类型
  router.push({
    path: '/backtest',
    query: { strategy: props.strategy.name },
  })
}

async function toggleFavorite() {
  try {
    const res = await strategySocialApi.toggleFavorite(props.strategy.id)
    userFavorited.value = res.data.favorited
    props.strategy.favorite_count = res.data.favorite_count
    emit('favorite-toggle', props.strategy.id, userFavorited.value)
  } catch (e) {
    console.error('Favorite failed:', e)
  }
}

async function handleRate(rating: number) {
  try {
    await strategySocialApi.rate(props.strategy.id, rating)
    userRating.value = rating
    emit('rate', props.strategy.id, rating)
  } catch (e) {
    console.error('Rate failed:', e)
  }
}

async function handleFavorite(_favorited: boolean) {
  // _favorited 是期望状态，实际以服务器返回为准
  try {
    const res = await strategySocialApi.toggleFavorite(props.strategy.id)
    userFavorited.value = res.data.favorited
    props.strategy.favorite_count = res.data.favorite_count
    emit('favorite-toggle', props.strategy.id, userFavorited.value)
  } catch (e) {
    console.error('Favorite failed:', e)
  }
}

async function handleComment(content: string, parentId?: number) {
  try {
    await strategySocialApi.addComment(props.strategy.id, content, parentId)
    // 刷新评论数
    props.strategy.comment_count += 1
  } catch (e) {
    console.error('Comment failed:', e)
  }
}
</script>

<style scoped lang="scss">
.strategy-card {
  background: var(--color-bg-secondary);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid var(--color-border);
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.is-official {
    border-left: 4px solid var(--color-primary);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;

  .strategy-info {
    flex: 1;
    min-width: 0;
  }

  .strategy-name {
    margin: 0 0 4px;
    font-size: 16px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .strategy-desc {
    margin: 0;
    font-size: 13px;
    color: var(--color-text-secondary);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.strategy-badges {
  display: flex;
  gap: 4px;
  flex-shrink: 0;

  .badge {
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 500;

    &.official {
      background: var(--color-primary-light);
      color: var(--color-primary);
    }

    &.risk {
      &.low {
        background: #e8f5e9;
        color: #2e7d32;
      }
      &.medium {
        background: #fff3e0;
        color: #ef6c00;
      }
      &.high {
        background: #ffebee;
        color: #c62828;
      }
    }
  }
}

.card-stats {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;

  .stat-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;

    .stat-label {
      color: var(--color-text-secondary);
    }

    .stat-value {
      font-weight: 600;
    }

    .rating-stars {
      display: flex;
      align-items: center;
      gap: 2px;

      .star {
        font-size: 14px;
        color: #ddd;

        &.filled {
          color: #ffc107;
        }
      }

      .rating-value {
        margin-left: 4px;
        font-weight: 600;
        font-size: 13px;
      }

      .stat-count {
        font-size: 11px;
        color: var(--color-text-tertiary);
      }
    }
  }
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;

  .tag {
    font-size: 11px;
    padding: 2px 8px;
    background: var(--color-bg-tertiary);
    border-radius: 4px;
    color: var(--color-text-secondary);
  }
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;

  .btn-small {
    padding: 4px 10px;
    font-size: 12px;
    flex: 1;
  }

  .btn-icon {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;

    &:hover {
      background: var(--color-bg-tertiary);
    }
  }
}
</style>
