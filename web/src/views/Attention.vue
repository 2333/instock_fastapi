<template>
  <div class="attention-page">
    <div class="page-header">
      <div class="header-left">
        <h1>我的关注</h1>
        <p class="subtitle">关注您感兴趣的股票，设置提醒条件</p>
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
        :key="stock.id"
        class="stock-card"
        :class="{ 'card-editing': editingId === stock.id }"
      >
        <div class="card-header">
          <div class="stock-info">
            <span class="stock-code">{{ stock.code }}</span>
            <span class="group-badge" :class="stock.group">{{ groupLabel(stock.group) }}</span>
          </div>
          <div class="card-actions">
            <button class="btn-icon" @click.stop="toggleEdit(stock)" title="编辑">
              ✏️
            </button>
            <button class="btn-icon" @click.stop="removeStock(stock.id)" title="取消关注">
              ×
            </button>
          </div>
        </div>

        <div class="stock-name">{{ stock.stock_name || '未知' }}</div>

        <!-- Edit Panel -->
        <div v-if="editingId === stock.id" class="edit-panel">
          <div class="form-group">
            <label>分组</label>
            <select v-model="editForm.group" class="form-select">
              <option value="watch">自选</option>
              <option value="observe">观察</option>
              <option value="long-term">长期关注</option>
            </select>
          </div>
          <div class="form-group">
            <label>备注</label>
            <textarea v-model="editForm.notes" class="form-textarea" placeholder="添加备注..." rows="2"></textarea>
          </div>
          <div class="edit-actions">
            <button class="btn btn-small btn-secondary" @click="cancelEdit">取消</button>
            <button class="btn btn-small btn-primary" @click="saveEdit(stock.id)">保存</button>
          </div>
        </div>

        <div v-else class="card-summary">
          <div v-if="stock.notes" class="notes-preview">{{ stock.notes }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { attentionApi } from '@/api'

interface AttentionItem {
  id: number
  ts_code: string
  code: string
  stock_name: string | null
  created_at: string | null
  group: string
  notes: string | null
}

const loading = ref(false)
const searchQuery = ref('')
const attentionList = ref<AttentionItem[]>([])
const editingId = ref<number | null>(null)
const editForm = ref<{
  group: string
  notes: string
}>({
  group: 'watch',
  notes: '',
})

const groupLabel = (group: string) => {
  const labels: Record<string, string> = {
    watch: '自选',
    observe: '观察',
    'long-term': '长期关注',
  }
  return labels[group] || group
}

const fetchAttention = async () => {
  loading.value = true
  try {
    attentionList.value = await attentionApi.getList()
  } catch (e) {
    console.error('Failed to fetch attention list:', e)
  } finally {
    loading.value = false
  }
}

const addStock = async () => {
  if (!searchQuery.value) return
  const code = searchQuery.value

  try {
    await attentionApi.add(code, 'watch')
    searchQuery.value = ''
    await fetchAttention()
  } catch (e) {
    console.error('Failed to add attention:', e)
  }
}

const removeStock = async (id: number) => {
  if (!confirm('确定取消关注该股票？')) return
  try {
    const stock = attentionList.value.find(s => s.id === id)
    if (stock) {
      await attentionApi.remove(stock.code)
      await fetchAttention()
    }
  } catch (e) {
    console.error('Failed to remove attention:', e)
  }
}

const toggleEdit = (stock: AttentionItem) => {
  if (editingId.value === stock.id) {
    editingId.value = null
  } else {
    editingId.value = stock.id
    editForm.value = {
      group: stock.group || 'watch',
      notes: stock.notes || '',
    }
  }
}

const cancelEdit = () => {
  editingId.value = null
}

const saveEdit = async (id: number) => {
  try {
    const updates: any = {}
    if (editForm.value.group) updates.group = editForm.value.group
    if (editForm.value.notes !== undefined) updates.notes = editForm.value.notes || null

    await attentionApi.update(id, updates)
    editingId.value = null
    await fetchAttention()
  } catch (e) {
    console.error('Failed to update attention:', e)
    alert('保存失败')
  }
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

.btn-secondary {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.8);
}

.btn-icon {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.stock-card {
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.2s;
  position: relative;

  &:hover {
    background: rgba(41, 98, 255, 0.08);
    border-color: rgba(41, 98, 255, 0.25);
  }

  &.card-editing {
    border-color: rgba(41, 98, 255, 0.5);
    background: rgba(41, 98, 255, 0.06);
  }
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.stock-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-code {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.group-badge {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  font-weight: 500;

  &.watch { background: rgba(41, 98, 255, 0.15); color: #9ab7ff; }
  &.observe { background: rgba(255, 152, 0, 0.15); color: #FFB74D; }
  &.long-term { background: rgba(0, 200, 83, 0.15); color: #69F0AE; }
}

.card-actions {
  display: flex;
  gap: 4px;
}

.stock-name {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;
}

.card-summary {
  .notes-preview {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.5);
    margin-bottom: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .alerts-badge {
    font-size: 12px;
    color: #FFD54F;
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.edit-panel {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.form-group {
  margin-bottom: 12px;

  label {
    display: block;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 6px;
  }
}

.form-select,
.form-textarea {
  width: 100%;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  color: #fff;
  font-size: 13px;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }
}

.form-textarea {
  resize: vertical;
  min-height: 50px;
}

.alert-fields {
  .field-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .field-label {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
    width: 70px;
  }

  .field-inputs {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 6px;

    .input-mini {
      flex: 1;
      min-width: 0;
      padding: 6px 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 4px;
      color: #fff;
      font-size: 12px;

      &:focus {
        outline: none;
        border-color: #2962FF;
      }
    }
  }
}

.edit-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 12px;

  .btn-small {
    padding: 6px 12px;
    font-size: 12px;
  }
}

/* 快速预警模态框 */
.alert-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.alert-modal {
  background: var(--color-bg-primary);
  border-radius: 8px;
  width: 100%;
  max-width: 400px;
  padding: 20px;
}

.alert-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    font-size: 16px;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
  }
}

.alert-modal-body {
  .form-group {
    margin-bottom: 12px;

    label {
      display: block;
      margin-bottom: 4px;
      font-size: 13px;
      font-weight: 500;
    }

    input,
    select {
      width: 100%;
      padding: 6px 10px;
      border: 1px solid var(--color-border);
      border-radius: 4px;
      font-size: 13px;
    }
  }
}

.alert-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}
</style>
