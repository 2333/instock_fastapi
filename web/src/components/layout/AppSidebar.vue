<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <button class="collapse-btn" @click="toggleCollapse">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline :points="collapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'" />
        </svg>
      </button>
    </div>

    <nav class="sidebar-nav">
      <div class="nav-section">
        <span v-if="!collapsed" class="nav-section-title">{{ t('sidebar_watchlist') }}</span>
        <ul class="nav-list">
          <li v-for="stock in watchlist" :key="stock.code" class="nav-item">
            <router-link :to="`/stock/${stock.code}`" class="nav-link">
              <div class="stock-info">
                <span class="stock-code">{{ stock.code }}</span>
                <span class="stock-name">{{ stock.name }}</span>
              </div>
            </router-link>
          </li>
          <li v-if="!watchlist.length && !collapsed" class="nav-item nav-empty">{{ t('sidebar_watchlist_empty') }}</li>
        </ul>
      </div>

      <div class="nav-section">
        <span v-if="!collapsed" class="nav-section-title">{{ t('sidebar_quick_actions') }}</span>
        <ul class="nav-list">
          <li class="nav-item">
            <button class="nav-btn" @click="showAddStock = true">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              <span v-if="!collapsed">{{ t('sidebar_add_stock') }}</span>
            </button>
          </li>
          <li class="nav-item">
            <button class="nav-btn" @click="refreshAll">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
                <path d="M21 3v5h-5" />
              </svg>
              <span v-if="!collapsed">{{ t('sidebar_refresh_all') }}</span>
            </button>
          </li>
        </ul>
      </div>
    </nav>

    <Teleport to="body">
      <div v-if="showAddStock" class="modal-overlay" @click.self="showAddStock = false">
        <div class="modal">
          <div class="modal-header">
            <h3>{{ t('sidebar_add_watchlist') }}</h3>
            <button class="close-btn" @click="showAddStock = false">×</button>
          </div>
          <div class="modal-body">
            <input 
              v-model="newStockCode" 
              type="text" 
              :placeholder="t('sidebar_add_placeholder')"
              class="stock-input"
              @keyup.enter="addStock"
            />
            <button class="btn btn-primary" @click="addStock">{{ t('sidebar_add_submit') }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>

<script setup lang="ts">
import { inject, onMounted, ref } from 'vue'
import { attentionApi } from '@/api'
import { useLocale } from '@/composables/useLocale'

interface StockItem {
  code: string
  name: string
}

const collapsed = ref(false)
const showAddStock = ref(false)
const newStockCode = ref('')
const watchlist = ref<StockItem[]>([])
const showNotification = inject<(type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => void>('showNotification')
const { t } = useLocale()

const toggleCollapse = () => {
  collapsed.value = !collapsed.value
}

const refreshAll = async () => {
  await loadWatchlist()
  showNotification?.('success', t('sidebar_watchlist_refreshed'))
}

const normalizeCode = (item: any): string => {
  if (item?.code) return String(item.code)
  if (item?.symbol) return String(item.symbol)
  if (item?.ts_code) return String(item.ts_code).split('.')[0]
  return ''
}

const normalizeName = (item: any): string => {
  return item?.name || item?.stock_name || item?.symbol || '-'
}

const loadWatchlist = async () => {
  try {
    const list = await attentionApi.getList()
    watchlist.value = (list || [])
      .map((item: any) => ({
        code: normalizeCode(item),
        name: normalizeName(item),
      }))
      .filter((x: StockItem) => !!x.code)
  } catch (e) {
    watchlist.value = []
    showNotification?.('error', t('sidebar_load_failed'))
  }
}

const addStock = async () => {
  const code = newStockCode.value.trim()
  if (!code) return
  try {
    await attentionApi.add(code)
    await loadWatchlist()
    showNotification?.('success', `${t('sidebar_added_prefix')} ${code} ${t('sidebar_added_suffix')}`)
    newStockCode.value = ''
    showAddStock.value = false
  } catch (e: any) {
    showNotification?.('error', e?.message || t('sidebar_add_failed'))
  }
}

onMounted(() => {
  loadWatchlist()
})
</script>

<style scoped lang="scss">
.app-sidebar {
  width: 280px;
  height: 100%;
  min-height: 0;
  background: rgba(26, 26, 26, 0.98);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;

  &.collapsed {
    width: 64px;
  }
}

.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 0;
}

.nav-section {
  margin-bottom: 24px;
}

.nav-section-title {
  display: block;
  padding: 0 16px;
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.4);
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  margin-bottom: 2px;
}

.nav-empty {
  padding: 10px 16px;
  color: rgba(255, 255, 255, 0.45);
  font-size: 12px;
}

.nav-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  text-decoration: none;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
  }
}

.stock-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stock-code {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.stock-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: calc(100% - 32px);
  margin: 0 16px;
  padding: 10px 12px;
  border: none;
  border-radius: 8px;
  background: rgba(41, 98, 255, 0.1);
  color: #2962FF;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(41, 98, 255, 0.2);
  }
}

.app-sidebar.collapsed {
  .nav-link {
    justify-content: center;
    padding: 10px 8px;
  }

  .stock-info {
    align-items: center;
  }

  .stock-name,
  .stock-price {
    display: none;
  }

  .stock-code {
    font-size: 11px;
  }

  .nav-btn {
    width: 44px;
    margin: 0 auto;
    justify-content: center;
    padding: 10px 0;
    gap: 0;
  }
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  width: 400px;
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
  }
}

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 20px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }
}

.modal-body {
  padding: 20px;
}

.stock-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  margin-bottom: 16px;
  box-sizing: border-box;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }

  &::placeholder {
    color: rgba(255, 255, 255, 0.4);
  }
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #2962FF;
  color: white;

  &:hover {
    background: #1E53E5;
  }
}
</style>
