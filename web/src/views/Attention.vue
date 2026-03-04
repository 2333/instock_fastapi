<template>
  <div class="attention-page">
    <div class="page-header">
      <div class="header-left">
        <h1>我的关注</h1>
        <p class="subtitle">关注您感兴趣的股票</p>
      </div>
      <div class="header-right">
        <div class="search-box">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="搜索股票代码..." 
            class="search-input"
            @keyup.enter="addStock"
          >
        </div>
        <button class="btn btn-primary" @click="addStock" :disabled="!searchQuery">
          添加关注
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="attentionList.length === 0" class="empty-state">
      <p>暂无关注的股票</p>
      <p class="hint">搜索股票代码并添加关注</p>
    </div>

    <div v-else class="stock-grid">
      <div 
        v-for="stock in attentionList" 
        :key="stock.ts_code"
        class="stock-card"
        @click="$router.push(`/stock/${stock.code}`)"
      >
        <div class="stock-header">
          <div class="stock-code">{{ stock.code }}</div>
          <button 
            class="btn-remove" 
            @click.stop="removeStock(stock.code)"
            title="取消关注"
          >
            ×
          </button>
        </div>
        <div class="stock-name">{{ stock.stock_name || '未知' }}</div>
        <div class="stock-date">{{ formatDate(stock.created_at) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { attentionApi } from '@/api'

const loading = ref(false)
const searchQuery = ref('')
const attentionList = ref<any[]>([])

const fetchAttention = async () => {
  loading.value = true
  try {
    const data = await attentionApi.getList()
    attentionList.value = data || []
  } catch (e) {
    console.error('Failed to fetch attention list:', e)
  } finally {
    loading.value = false
  }
}

const addStock = async () => {
  if (!searchQuery.value) return
  
  try {
    await attentionApi.add(searchQuery.value)
    searchQuery.value = ''
    await fetchAttention()
  } catch (e) {
    console.error('Failed to add attention:', e)
  }
}

const removeStock = async (code: string) => {
  try {
    await attentionApi.remove(code)
    await fetchAttention()
  } catch (e) {
    console.error('Failed to remove attention:', e)
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  fetchAttention()
})
</script>

<style scoped lang="scss">
.attention-page {
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

.header-right {
  display: flex;
  gap: 12px;
}

.search-box {
  .search-input {
    padding: 10px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
    width: 200px;

    &:focus {
      outline: none;
      border-color: #2962FF;
    }

    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
    }
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

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-primary {
  background: #2962FF;
  color: white;

  &:hover:not(:disabled) {
    background: #1E53E5;
  }
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  background: rgba(26, 26, 26, 0.5);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.6);

  .hint {
    margin-top: 8px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.4);
  }
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #2962FF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.stock-card {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(41, 98, 255, 0.1);
    border-color: rgba(41, 98, 255, 0.3);
  }
}

.stock-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.stock-code {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.btn-remove {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 23, 68, 0.1);
  color: #FF1744;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 23, 68, 0.2);
  }
}

.stock-name {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;
}

.stock-date {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}
</style>
