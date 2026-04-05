<template>
  <div class="notification-bell" ref="containerRef">
    <button class="bell-btn" @click="toggleDropdown" title="通知">
      <span class="bell-icon">🔔</span>
      <span v-if="unreadCount > 0" class="badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
    </button>

    <div v-if="showDropdown" class="dropdown">
      <div class="dropdown-header">
        <span>通知中心</span>
        <button v-if="unreadCount > 0" class="mark-all-btn" @click="markAllRead">全部已读</button>
      </div>
      <div class="dropdown-body">
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="notifications.length === 0" class="empty">暂无通知</div>
        <div v-else class="notification-list">
          <div
            v-for="notif in notifications"
            :key="notif.id"
            class="notif-item"
            :class="{ unread: !notif.is_read }"
            @click="handleClick(notif)"
          >
            <div class="notif-title">{{ notif.title }}</div>
            <div class="notif-message">{{ notif.message }}</div>
            <div class="notif-time">{{ formatTime(notif.created_at) }}</div>
          </div>
        </div>
      </div>
      <div v-if="hasMore" class="dropdown-footer">
        <button class="view-all-btn" @click="goToAll">查看全部</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { alertApi } from '@/api/alert'

const router = useRouter()
const showDropdown = ref(false)
const loading = ref(false)
const unreadCount = ref(0)
const notifications = ref<any[]>([])
const hasMore = ref(false)
const containerRef = ref<HTMLElement | null>(null)

const LIMIT = 10

onMounted(async () => {
  await fetchUnreadCount()
  await fetchNotifications()
})

async function fetchUnreadCount() {
  try {
    const res = await alertApi.getUnreadCount()
    unreadCount.value = res.data?.unread_count || 0
  } catch (e) {
    console.error('Failed to fetch unread count:', e)
  }
}

async function fetchNotifications() {
  loading.value = true
  try {
    const res = await alertApi.listNotifications(LIMIT)
    notifications.value = res.data || []
    hasMore.value = (res.data || []).length >= LIMIT
  } catch (e) {
    console.error('Failed to fetch notifications:', e)
  } finally {
    loading.value = false
  }
}

function toggleDropdown() {
  if (showDropdown.value) {
    closeDropdown()
  } else {
    showDropdown.value = true
    fetchNotifications()
  }
}

function closeDropdown() {
  showDropdown.value = false
}

async function markAllRead() {
  try {
    // 逐条标记已读（后端暂不支持批量）
    const unread = notifications.value.filter(n => !n.is_read)
    await Promise.all(unread.map(n => alertApi.markRead(n.id)))
    await fetchUnreadCount()
    await fetchNotifications()
  } catch (e) {
    console.error('Failed to mark all read:', e)
  }
}

async function handleClick(notif: any) {
  if (!notif.is_read) {
    try {
      await alertApi.markRead(notif.id)
      await fetchUnreadCount()
    } catch (e) {
      console.error('Failed to mark read:', e)
    }
  }

  // 根据 payload 跳转
  const payload = notif.payload || {}
  if (payload.code) {
    router.push(`/stock/${payload.code}`)
  } else if (payload.alert_id) {
    router.push('/alerts')
  }
  closeDropdown()
}

function goToAll() {
  router.push('/alerts')
  closeDropdown()
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

// 点击外部关闭
function onClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    closeDropdown()
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped lang="scss">
.notification-bell {
  position: relative;
  display: inline-block;
}

.bell-btn {
  position: relative;
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: background 0.2s;

  &:hover {
    background: var(--color-bg-secondary);
  }

  .badge {
    position: absolute;
    top: -2px;
    right: -2px;
    background: var(--color-error);
    color: white;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 5px;
    border-radius: 10px;
    min-width: 16px;
    text-align: center;
  }
}

.dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  width: 320px;
  max-height: 400px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  overflow: hidden;
  margin-top: 8px;
}

.dropdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  font-weight: 600;

  .mark-all-btn {
    background: none;
    border: none;
    color: var(--color-primary);
    font-size: 12px;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }
}

.dropdown-body {
  max-height: 300px;
  overflow-y: auto;
}

.loading,
.empty {
  padding: 32px;
  text-align: center;
  color: var(--color-text-secondary);
}

.notification-list {
  display: flex;
  flex-direction: column;
}

.notif-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background 0.2s;

  &:hover {
    background: var(--color-bg-secondary);
  }

  &.unread {
    background: var(--color-primary-light);
  }

  .notif-title {
    font-weight: 600;
    margin-bottom: 4px;
    font-size: 14px;
  }

  .notif-message {
    font-size: 12px;
    color: var(--color-text-secondary);
    margin-bottom: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .notif-time {
    font-size: 11px;
    color: var(--color-text-tertiary);
  }
}

.dropdown-footer {
  padding: 8px 16px;
  border-top: 1px solid var(--color-border);
  text-align: center;

  .view-all-btn {
    background: none;
    border: none;
    color: var(--color-primary);
    font-size: 12px;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
