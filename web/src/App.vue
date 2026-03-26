<template>
  <div class="app-container">
    <template v-if="isAuthenticated && !isLoginPage">
      <AppHeader @refresh="handleRefresh" @settings="openSettings" />

      <div class="app-content">
        <AppSidebar v-if="showSidebar" />

        <main class="main-viewport" :class="{ 'workspace-viewport': !showSidebar }">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </div>
    </template>
    <template v-else>
      <router-view />
    </template>

    <LoadingOverlay :loading="isLoading" :text="loadingText" />
    <NotificationContainer ref="notificationRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, provide, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import NotificationContainer from '@/components/common/NotificationContainer.vue'
import { authApi } from '@/api'
import { loadUserPreferences } from '@/composables/useUserPreferences'

const router = useRouter()
const route = useRoute()
const isLoading = ref(false)
const loadingText = ref('')
const notificationRef = ref<InstanceType<typeof NotificationContainer> | null>(null)

const isAuthenticated = computed(() => authApi.isAuthenticated())
const isLoginPage = computed(() => route.path === '/login')
const showSidebar = computed(() => !route.meta.hideSidebar)

const handleRefresh = () => {
  if (notificationRef.value) {
    notificationRef.value.success('数据刷新成功', '完成')
  }
}

const openSettings = () => {
  router.push('/settings')
}

const handleLogout = () => {
  authApi.removeToken()
  router.push('/login')
}

provide('showNotification', (type: 'success' | 'error' | 'warning' | 'info', message: string, title?: string) => {
  if (notificationRef.value) {
    notificationRef.value[type](message, title)
  }
})

provide('handleLogout', handleLogout)
provide('isAuthenticated', isAuthenticated)

onMounted(async () => {
  if (authApi.isAuthenticated()) {
    try {
      await authApi.getMe()
      await loadUserPreferences(true)
    } catch (e) {
      authApi.removeToken()
    }
  }
})
</script>

<style scoped lang="scss">
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0d0d0d;
  overflow: hidden;
}

.app-content {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.main-viewport {
  flex: 1;
  min-height: 0;
  overflow: auto;
  background: #0d0d0d;
}

.workspace-viewport {
  width: 100%;
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
