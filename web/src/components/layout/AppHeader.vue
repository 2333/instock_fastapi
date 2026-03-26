<template>
  <header class="app-header">
    <div class="header-left">
      <router-link :to="preferences.defaultHome" class="logo">
        <svg class="logo-icon" viewBox="0 0 32 32" fill="none">
          <path
            d="M16 2L4 8V24L16 30L28 24V8L16 2Z"
            fill="url(#logo-gradient)"
          />
          <path
            d="M16 2V30M4 8L16 14L28 8M4 16L16 22L28 16M4 24L16 18L28 24"
            stroke="rgba(255,255,255,0.3)"
            stroke-width="1"
          />
          <defs>
            <linearGradient id="logo-gradient" x1="4" y1="2" x2="28" y2="30">
              <stop stop-color="#2962FF" />
              <stop offset="1" stop-color="#00C853" />
            </linearGradient>
          </defs>
        </svg>
        <span class="logo-text">InStock</span>
      </router-link>
    </div>

    <div class="header-center">
      <nav class="header-nav">
        <router-link
          to="/"
          class="nav-item"
          :class="{ active: $route.path === '/' }"
        >
          <span class="nav-icon">📊</span>
          <span>{{ t("nav_dashboard") }}</span>
        </router-link>
        <router-link
          to="/workspace"
          class="nav-item"
          :class="{ active: $route.path.startsWith('/workspace') }"
        >
          <span class="nav-icon">🖥️</span>
          <span>{{ t('nav_workspace') }}</span>
        </router-link>
        <router-link
          to="/stocks"
          class="nav-item"
          :class="{ active: $route.path.startsWith('/stocks') }"
        >
          <span class="nav-icon">📈</span>
          <span>{{ t("nav_stocks") }}</span>
        </router-link>
        <router-link
          to="/patterns"
          class="nav-item"
          :class="{ active: $route.path === '/patterns' }"
        >
          <span class="nav-icon">🔍</span>
          <span>{{ t("nav_patterns") }}</span>
        </router-link>
        <router-link
          to="/backtest"
          class="nav-item"
          :class="{ active: $route.path === '/backtest' }"
        >
          <span class="nav-icon">⚡</span>
          <span>{{ t("nav_backtest") }}</span>
        </router-link>
        <router-link
          to="/selection"
          class="nav-item"
          :class="{ active: $route.path === '/selection' }"
        >
          <span class="nav-icon">🎯</span>
          <span>{{ t("nav_selection") }}</span>
        </router-link>
      </nav>
    </div>

    <div class="header-right">
      <div class="build-badge" :title="`build ${appGitSha}`">
        v{{ appVersion }}
      </div>

      <div class="market-status" :class="{ active: marketOpen }">
        <span class="status-dot"></span>
        <span class="status-text">{{
          marketOpen ? t("market_open") : t("market_closed")
        }}</span>
      </div>

      <div class="header-actions">
        <button class="action-btn" :title="t('refresh')" @click="refreshData">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
          </svg>
        </button>
        <button class="action-btn" :title="t('settings')" @click="openSettings">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="3" />
            <path
              d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
            />
          </svg>
        </button>
        <button
          class="action-btn lang-btn"
          title="Language"
          @click="toggleLocale"
        >
          <span>{{ t("lang_switch") }}</span>
        </button>
      </div>

      <div class="user-menu">
        <template v-if="currentUser">
          <button class="user-btn" @click="toggleUserMenu">
            <div class="user-avatar">
              {{ currentUser.username?.charAt(0).toUpperCase() }}
            </div>
            <span class="user-name">{{ currentUser.username }}</span>
          </button>
          <div v-if="showUserMenu" class="user-dropdown">
            <router-link
              to="/settings"
              class="dropdown-item"
              @click="showUserMenu = false"
              >{{ t("preferences") }}</router-link
            >
            <hr class="dropdown-divider" />
            <a
              href="#"
              class="dropdown-item"
              @click.prevent="handleLogoutClick"
              >{{ t("logout") }}</a
            >
          </div>
        </template>
        <template v-else>
          <router-link to="/login" class="login-link">登录</router-link>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useLocale } from "@/composables/useLocale";
import { authApi } from "@/api";
import { useUserPreferences } from "@/composables/useUserPreferences";

const router = useRouter();
const emit = defineEmits<{
  (e: "refresh"): void;
  (e: "settings"): void;
}>();

const marketOpen = ref(false);
const showUserMenu = ref(false);
const { t, toggleLocale } = useLocale();
const currentUser = ref<any>(null);
const { preferences, loadUserPreferences } = useUserPreferences();
const appVersion = __APP_VERSION__;
const appGitSha = __APP_GIT_SHA__;

const refreshData = () => emit("refresh");
const openSettings = () => emit("settings");

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value;
};

const handleLogoutClick = () => {
  authApi.removeToken();
  showUserMenu.value = false;
  router.push("/login");
};

const checkMarketStatus = () => {
  const now = new Date();
  const hour = now.getHours();
  const day = now.getDay();

  if (day === 0 || day === 6) {
    marketOpen.value = false;
    return;
  }

  if ((hour >= 9 && hour < 11) || (hour >= 13 && hour < 15)) {
    marketOpen.value = true;
  } else {
    marketOpen.value = false;
  }
};

let intervalId: number | null = null;

onMounted(async () => {
  checkMarketStatus();
  intervalId = window.setInterval(checkMarketStatus, 60000);
  await loadUserPreferences(true);

  if (authApi.isAuthenticated()) {
    try {
      currentUser.value = await authApi.getMe();
    } catch (e) {
      authApi.removeToken();
    }
  }
});

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId);
});
</script>

<style scoped lang="scss">
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 20px;
  background: rgba(26, 26, 26, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  transition: opacity 0.2s;

  &:hover {
    opacity: 0.8;
  }
}

.logo-icon {
  width: 32px;
  height: 32px;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(135deg, #2962ff, #00c853);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.header-nav {
  display: flex;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.6);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.9);
  }

  &.active {
    background: rgba(41, 98, 255, 0.15);
    color: #2962ff;
  }

  .nav-icon {
    font-size: 16px;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.build-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 6px 10px;
  border: 1px solid rgba(41, 98, 255, 0.28);
  border-radius: 999px;
  background: rgba(41, 98, 255, 0.12);
  color: #9fb8ff;
  font-size: 12px;
  font-weight: 600;
  font-family: "JetBrains Mono", monospace;
}

.market-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(255, 23, 68, 0.1);
  color: #ff1744;
  font-size: 12px;
  font-weight: 500;

  &.active {
    background: rgba(0, 200, 83, 0.1);
    color: #00c853;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s infinite;
  }
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }
}

.lang-btn {
  width: auto;
  min-width: 36px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 600;
}

.user-menu {
  position: relative;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2962ff, #00c853);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: white;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
}

.user-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  min-width: 160px;
  background: #1a1a1a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 8px 0;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.dropdown-item {
  display: block;
  padding: 10px 16px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.9);
  }
}

.dropdown-divider {
  margin: 8px 0;
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.login-link {
  padding: 8px 16px;
  border-radius: 8px;
  background: #2962ff;
  color: #fff;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;

  &:hover {
    background: #1e53e5;
  }
}
</style>
