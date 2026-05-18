<template>
  <div class="settings-page">
    <div class="page-header">
      <h1>{{ t('settings_page_title') }}</h1>
      <p class="subtitle">{{ t('settings_page_subtitle') }}</p>
    </div>

    <main class="settings-card">
      <section class="settings-section">
        <h2>{{ t('settings_current_section') }}</h2>

        <div class="setting-item">
          <div class="setting-info">
            <h4>{{ t('settings_language_label') }}</h4>
            <p>{{ t('settings_language_help') }}</p>
          </div>
          <select v-model="settings.language" class="setting-select" :disabled="isSaving">
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </div>

        <div class="setting-item">
          <div class="setting-info">
            <h4>{{ t('settings_default_home_label') }}</h4>
            <p>{{ t('settings_default_home_help') }}</p>
          </div>
          <div class="setting-static">{{ t('settings_default_home_value') }}</div>
        </div>
      </section>

      <section class="settings-section settings-section--muted">
        <h2>{{ t('settings_unavailable_section') }}</h2>
        <p>
          {{ t('settings_unavailable_help') }}
        </p>
      </section>

      <p v-if="statusMessage" class="settings-status" :class="`is-${statusTone}`">
        {{ statusMessage }}
      </p>

      <div class="settings-footer">
        <button class="btn btn-primary" @click="saveSettings" :disabled="isSaving">
          {{ isSaving ? t('settings_saving') : t('settings_save') }}
        </button>
        <button class="btn btn-secondary" @click="resetSettings" :disabled="isSaving">
          {{ t('settings_reset') }}
        </button>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { authApi } from '@/api'
import { buildSettingsExtra, setUserPreferences } from '@/composables/useUserPreferences'
import { applyLocaleFromSettings, normalizeLocale, useLocale, type Locale } from '@/composables/useLocale'

interface AuthSettingsSnapshot {
  language?: string | null
  extra?: unknown
}

const { locale, t } = useLocale()

const settings = reactive({
  language: locale.value as Locale,
})

const isSaving = ref(false)
const statusMessage = ref('')
const statusTone = ref<'success' | 'error'>('success')
const persisted = ref<AuthSettingsSnapshot>({
  language: locale.value,
  extra: null,
})

const toBackendLanguage = (value: Locale): string => {
  return value === 'en' ? 'en-US' : 'zh-CN'
}

const setStatus = (message: string, tone: 'success' | 'error') => {
  statusMessage.value = message
  statusTone.value = tone
}

const applyPersistedSettings = (snapshot: AuthSettingsSnapshot | null | undefined) => {
  settings.language = normalizeLocale(snapshot?.language ?? locale.value)
}

const syncDefaultHomeResidue = () => {
  setUserPreferences({ defaultHome: '/' })
}

const loadSettings = async () => {
  try {
    const response = await authApi.getSettings()
    persisted.value = response ?? {}
    applyPersistedSettings(persisted.value)
    applyLocaleFromSettings(persisted.value)
  } catch (error) {
    applyPersistedSettings(persisted.value)
    setStatus(t('settings_load_fallback'), 'error')
  } finally {
    syncDefaultHomeResidue()
  }
}

const saveSettings = async () => {
  isSaving.value = true
  statusMessage.value = ''

  try {
    const nextExtra = buildSettingsExtra(persisted.value?.extra, { defaultHome: '/' })
    const response = await authApi.updateSettings({
      language: toBackendLanguage(settings.language),
      extra: nextExtra,
    })

    persisted.value = response ?? {
      ...persisted.value,
      language: toBackendLanguage(settings.language),
      extra: nextExtra,
    }

    applyPersistedSettings(persisted.value)
    applyLocaleFromSettings(persisted.value)
    syncDefaultHomeResidue()
    setStatus(t('settings_saved'), 'success')
  } catch (error) {
    setStatus(t('settings_save_failed'), 'error')
  } finally {
    isSaving.value = false
  }
}

const resetSettings = async () => {
  settings.language = 'zh'
  await saveSettings()
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped lang="scss">
.settings-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.settings-card {
  max-width: 860px;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 24px;
}

.settings-section {
  display: grid;
  gap: 20px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
  }
}

.settings-section + .settings-section {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.settings-section--muted {
  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.68);
    line-height: 1.6;
  }
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);

  &:first-of-type {
    border-top: none;
    padding-top: 0;
  }
}

.setting-info {
  h4 {
    margin: 0 0 6px;
    font-size: 16px;
    font-weight: 600;
  }

  p {
    margin: 0;
    color: rgba(255, 255, 255, 0.68);
    line-height: 1.5;
  }
}

.setting-select,
.setting-static {
  min-width: 220px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
}

.setting-select {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: #fff;

  &:focus {
    outline: none;
    border-color: #2962ff;
  }
}

.setting-static {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.86);
  text-align: center;
}

.settings-status {
  margin: 24px 0 0;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 14px;
}

.settings-status.is-success {
  background: rgba(0, 200, 83, 0.12);
  border: 1px solid rgba(0, 200, 83, 0.25);
  color: #7de3a3;
}

.settings-status.is-error {
  background: rgba(255, 92, 122, 0.12);
  border: 1px solid rgba(255, 92, 122, 0.25);
  color: #ff9caf;
}

.settings-footer {
  display: flex;
  gap: 12px;
  margin-top: 24px;
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
  background: #2962ff;
  color: white;

  &:hover:not(:disabled) {
    background: #1e53e5;
  }
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.8);
}

@media (max-width: 760px) {
  .setting-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .setting-select,
  .setting-static {
    width: 100%;
    min-width: 0;
  }

  .settings-footer {
    flex-direction: column;
  }
}
</style>
