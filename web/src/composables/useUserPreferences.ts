import { computed, ref } from 'vue'
import { authApi } from '@/api'

export type HomeRoute = '/' | '/workspace'

export interface UserPreferences {
  defaultHome: HomeRoute
}

const STORAGE_KEY = 'instock_user_preferences'

const DEFAULT_PREFERENCES: UserPreferences = {
  defaultHome: '/',
}

const normalizeHomeRoute = (value: unknown): HomeRoute => {
  return value === '/workspace' ? '/workspace' : '/'
}

const normalizePreferences = (value: unknown): UserPreferences => {
  const raw = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const nested = raw.ui_preferences && typeof raw.ui_preferences === 'object'
    ? raw.ui_preferences as Record<string, unknown>
    : {}

  return {
    defaultHome: normalizeHomeRoute(nested.defaultHome ?? raw.defaultHome),
  }
}

const readStoredPreferences = (): UserPreferences => {
  if (typeof window === 'undefined') return DEFAULT_PREFERENCES

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_PREFERENCES
    return {
      ...DEFAULT_PREFERENCES,
      ...normalizePreferences(JSON.parse(raw)),
    }
  } catch {
    return DEFAULT_PREFERENCES
  }
}

const userPreferences = ref<UserPreferences>(readStoredPreferences())

const persistPreferences = (preferences: UserPreferences) => {
  userPreferences.value = preferences
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
  }
}

export const getPreferredHomePath = () => userPreferences.value.defaultHome

export const buildSettingsExtra = (extra: unknown, preferences: Partial<UserPreferences>) => {
  const base = extra && typeof extra === 'object' ? { ...(extra as Record<string, unknown>) } : {}
  const uiPreferences =
    base.ui_preferences && typeof base.ui_preferences === 'object'
      ? { ...(base.ui_preferences as Record<string, unknown>) }
      : {}

  const merged = {
    ...base,
    defaultHome: normalizeHomeRoute(preferences.defaultHome ?? base.defaultHome),
    ui_preferences: {
      ...uiPreferences,
      defaultHome: normalizeHomeRoute(preferences.defaultHome ?? uiPreferences.defaultHome ?? base.defaultHome),
    },
  }

  return merged
}

export const loadUserPreferences = async (force = false) => {
  if (!authApi.isAuthenticated()) {
    return userPreferences.value
  }

  if (!force && userPreferences.value !== DEFAULT_PREFERENCES) {
    return userPreferences.value
  }

  try {
    const settings = await authApi.getSettings()
    const next = normalizePreferences(settings?.extra)
    persistPreferences(next)
    return next
  } catch {
    return userPreferences.value
  }
}

export const setUserPreferences = (preferences: Partial<UserPreferences>) => {
  const next = {
    ...userPreferences.value,
    ...normalizePreferences(preferences),
  }
  persistPreferences(next)
  return next
}

export function useUserPreferences() {
  return {
    preferences: computed(() => userPreferences.value),
    loadUserPreferences,
    setUserPreferences,
    getPreferredHomePath,
    buildSettingsExtra,
  }
}
