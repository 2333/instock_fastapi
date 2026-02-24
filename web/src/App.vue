<template>
  <div class="app-container">
    <AppHeader @refresh="handleRefresh" @settings="openSettings" />
    
    <div class="app-content">
      <AppSidebar />
      
      <main class="main-viewport">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
    
    <LoadingOverlay :loading="isLoading" :text="loadingText" />
    <NotificationContainer ref="notificationRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, provide, onMounted } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import NotificationContainer from '@/components/common/NotificationContainer.vue'

const isLoading = ref(false)
const loadingText = ref('')
const notificationRef = ref<InstanceType<typeof NotificationContainer> | null>(null)

const handleRefresh = () => {
  console.log('Refreshing application data...')
  if (notificationRef.value) {
    notificationRef.value.success('Data refreshed successfully', 'Success')
  }
}

const openSettings = () => {
  console.log('Opening settings...')
}

provide('showNotification', (type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => {
  if (notificationRef.value) {
    notificationRef.value[type](message, title)
  }
})

onMounted(() => {
  console.log('InStock application initialized')
})
</script>

<style scoped lang="scss">
.app-container {
  min-height: 100vh;
  background: #0d0d0d;
}

.app-content {
  display: flex;
  min-height: calc(100vh - 60px);
}

.main-viewport {
  flex: 1;
  overflow: auto;
  background: #0d0d0d;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
