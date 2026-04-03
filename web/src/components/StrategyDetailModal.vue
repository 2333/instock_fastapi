<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal" :style="{ maxWidth: '800px' }">
      <div class="modal-header">
        <div class="header-content">
          <h2>{{ strategy.name }}</h2>
          <div class="header-badges">
            <span v-if="strategy.is_official" class="badge official">官方</span>
            <span v-if="strategy.risk_level" class="badge risk" :class="strategy.risk_level">{{ riskLabel }}</span>
            <span v-if="strategy.suitable_market" class="badge market">{{ marketLabel }}</span>
          </div>
        </div>
        <button class="close-btn" @click="close">×</button>
      </div>

      <div class="modal-body">
        <div class="strategy-summary" v-if="strategy.description">
          <p>{{ strategy.description }}</p>
        </div>

        <!-- 社交指标 -->
        <div class="social-stats">
          <div class="stat">
            <span class="label">评分</span>
            <div class="rating">
              <span v-for="n in 5" :key="n" class="star" :class="{ filled: n <= Math.round(strategy.rating) }">
                ★
              </span>
              <span class="value">{{ strategy.rating.toFixed(1) }}</span>
              <span class="count">({{ strategy.rating_count }}人评价)</span>
            </div>
          </div>
          <div class="stat">
            <span class="label">收藏</span>
            <span class="value">{{ strategy.favorite_count }}</span>
          </div>
          <div class="stat">
            <span class="label">评论</span>
            <span class="value">{{ strategy.comment_count }}</span>
          </div>
          <div class="stat">
            <span class="label">回测</span>
            <span class="value">{{ strategy.backtest_count }}</span>
          </div>
        </div>

        <!-- 标签 -->
        <div v-if="strategy.tags && strategy.tags.length" class="tags-section">
          <span class="section-label">标签：</span>
          <span v-for="tag in strategy.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>

        <!-- 我的评分与收藏 -->
        <div class="user-actions">
          <div class="rating-section" v-if="userRating !== null">
            <span class="label">我的评分：</span>
            <div class="star-rating">
              <button v-for="n in 5" :key="n" @click="setRating(n)" class="star-btn">
                {{ n <= userRating ? '★' : '☆' }}
              </button>
            </div>
          </div>
          <div class="favorite-section" v-else>
            <button class="btn btn-secondary btn-small" @click="rateDialog = true">评分</button>
            <button class="btn btn-primary btn-small" @click="toggleFavorite">
              {{ userFavorited ? '已收藏' : '收藏' }}
            </button>
          </div>
        </div>

        <!-- 评论列表 -->
        <div class="comments-section">
          <h4>评论 ({{ comments.length }})</h4>
          <div class="comment-input">
            <textarea
              v-model="newComment"
              placeholder="写下你的看法..."
              rows="3"
            ></textarea>
            <button class="btn btn-primary btn-small" @click="submitComment">发表评论</button>
          </div>

          <div class="comment-list">
            <div v-for="comment in comments" :key="comment.id" class="comment-item">
              <div class="comment-header">
                <span class="comment-user">用户{{ comment.user_id }}</span>
                <span class="comment-time">{{ formatTime(comment.created_at) }}</span>
              </div>
              <div class="comment-content">{{ comment.content }}</div>
            </div>
          </div>
        </div>

        <!-- 参数展示（预留） -->
        <div class="params-section" v-if="strategy.params">
          <h4>策略参数</h4>
          <pre class="params-json">{{ JSON.stringify(strategy.params, null, 2) }}</pre>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="close">关闭</button>
        <button class="btn btn-primary" @click="copyAndBacktest">复制并回测</button>
      </div>
    </div>
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
    params?: Record<string, any>
  }
  userRating: number | null
  userFavorited: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'rate', rating: number): void
  (e: 'favorite', favorited: boolean): void
  (e: 'comment', content: string, parentId?: number): void
}>()

const comments = ref<any[]>([])
const newComment = ref('')
const rateDialog = ref(false)

const riskLabel = computed(() => {
  const labels: Record<string, string> = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
  }
  return labels[props.strategy.risk_level || ''] || ''
})

const marketLabel = computed(() => {
  const labels: Record<string, string> = {
    bull: '牛市',
    bear: '熊市',
    sideway: '震荡市',
  }
  return labels[props.strategy.suitable_market || ''] || ''
})

onMounted(async () => {
  await loadComments()
})

async function loadComments() {
  try {
    const res = await strategySocialApi.getComments(props.strategy.id, 50)
    comments.value = res.data || []
  } catch (e) {
    console.error('Failed to load comments:', e)
  }
}

function close() {
  emit('close')
}

function setRating(rating: number) {
  emit('rate', rating)
}

async function toggleFavorite() {
  try {
    const res = await strategySocialApi.toggleFavorite(props.strategy.id)
    emit('favorite', res.data.favorited)
  } catch (e) {
    console.error('Favorite failed:', e)
  }
}

async function submitComment() {
  if (!newComment.value.trim()) return
  try {
    await strategySocialApi.addComment(props.strategy.id, newComment.value)
    newComment.value = ''
    await loadComments()
    emit('comment', '')
  } catch (e) {
    console.error('Comment failed:', e)
  }
}

function copyAndBacktest() {
  // 复制策略参数到回测页面
  // 实际应调用策略复制 API，然后跳转
  router.push({
    path: '/backtest',
    query: { strategy: props.strategy.name },
  })
  close()
}

function formatTime(dateStr: string) {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`
  if (days < 7) return `${days} 天前`
  return d.toLocaleDateString('zh-CN')
}
</script>

<style scoped lang="scss">
.strategy-detail-modal {
  // Styles defined in parent overlay
}

.social-stats {
  display: flex;
  gap: 24px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 16px;

  .stat {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .label {
      font-size: 12px;
      color: var(--color-text-secondary);
    }

    .rating {
      display: flex;
      align-items: center;
      gap: 2px;

      .star {
        font-size: 16px;
        color: #ddd;

        &.filled {
          color: #ffc107;
        }
      }

      .value {
        margin-left: 4px;
        font-weight: 600;
        font-size: 14px;
      }

      .count {
        font-size: 11px;
        color: var(--color-text-tertiary);
        margin-left: 4px;
      }
    }

    .value {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-primary);
    }
  }
}

.tags-section {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;

  .section-label {
    font-size: 13px;
    color: var(--color-text-secondary);
    line-height: 20px;
  }

  .tag {
    font-size: 12px;
    padding: 2px 10px;
    background: var(--color-bg-tertiary);
    border-radius: 4px;
    color: var(--color-text-secondary);
  }
}

.user-actions {
  margin-bottom: 20px;
  padding: 12px;
  background: var(--color-bg-tertiary);
  border-radius: 8px;

  .rating-section {
    display: flex;
    align-items: center;
    gap: 12px;

    .label {
      font-size: 13px;
      color: var(--color-text-secondary);
    }

    .star-rating {
      display: flex;
      gap: 4px;

      .star-btn {
        background: none;
        border: none;
        font-size: 24px;
        cursor: pointer;
        color: #ddd;
        transition: color 0.2s;

        &:hover,
        &:focus {
          color: #ffc107;
        }
      }
    }
  }

  .favorite-section {
    display: flex;
    gap: 8px;
  }
}

.comments-section {
  h4 {
    margin: 0 0 12px;
    font-size: 15px;
  }

  .comment-input {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;

    textarea {
      flex: 1;
      padding: 8px 12px;
      border: 1px solid var(--color-border);
      border-radius: 6px;
      font-size: 13px;
      resize: vertical;
      min-height: 60px;

      &:focus {
        outline: none;
        border-color: var(--color-primary);
      }
    }
  }

  .comment-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 300px;
    overflow-y: auto;

    .comment-item {
      padding: 10px 12px;
      background: var(--color-bg-tertiary);
      border-radius: 6px;

      .comment-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;

        .comment-user {
          font-size: 12px;
          font-weight: 600;
        }

        .comment-time {
          font-size: 11px;
          color: var(--color-text-tertiary);
        }
      }

      .comment-content {
        font-size: 13px;
        line-height: 1.5;
      }
    }
  }
}

.params-section {
  margin-top: 20px;

  h4 {
    margin: 0 0 8px;
    font-size: 14px;
  }

  .params-json {
    background: var(--color-bg-tertiary);
    padding: 12px;
    border-radius: 6px;
    font-size: 12px;
    overflow-x: auto;
    margin: 0;
  }
}
</style>
