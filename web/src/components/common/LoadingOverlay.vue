<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="loading" class="loading-overlay">
        <div class="loading-content">
          <div class="spinner">
            <svg viewBox="0 0 50 50">
              <circle cx="25" cy="25" r="20" fill="none" stroke-width="4" stroke="rgba(255,255,255,0.1)" />
              <circle cx="25" cy="25" r="20" fill="none" stroke-width="4" stroke="url(#spinner-gradient)" stroke-linecap="round" stroke-dasharray="90, 150" stroke-dashoffset="0">
                <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="1s" repeatCount="indefinite" />
              </circle>
              <defs>
                <linearGradient id="spinner-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#2962FF" />
                  <stop offset="100%" stop-color="#00C853" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <p v-if="text" class="loading-text">{{ text }}</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  loading: boolean
  text?: string
}>()
</script>

<style scoped lang="scss">
.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(13, 13, 13, 0.85);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  width: 48px;
  height: 48px;

  svg {
    width: 100%;
    height: 100%;
  }
}

.loading-text {
  margin: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
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
