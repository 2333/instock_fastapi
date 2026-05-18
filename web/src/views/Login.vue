<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>InStock</h1>
        <p>{{ t('login_tagline') }}</p>
      </div>
      
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">{{ t('login_username') }}</label>
          <input 
            id="username"
            v-model="username" 
            type="text" 
            :placeholder="t('login_username_placeholder')"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="password">{{ t('login_password') }}</label>
          <input 
            id="password"
            v-model="password" 
            type="password" 
            :placeholder="t('login_password_placeholder')"
            required
          />
        </div>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? t('login_submitting') : t('login_submit') }}
        </button>
      </form>
      
      <div class="login-footer">
        <p>{{ t('login_register_prompt') }} <a href="#" @click.prevent="showRegister = true">{{ t('login_register_link') }}</a></p>
      </div>
    </div>

    <!-- Register Modal -->
    <div v-if="showRegister" class="modal-overlay" @click="showRegister = false">
      <div class="modal-card" @click.stop>
        <h2>{{ t('register_title') }}</h2>
        <form @submit.prevent="handleRegister" class="login-form">
          <div class="form-group">
            <label for="reg-username">{{ t('login_username') }}</label>
            <input 
              id="reg-username"
              v-model="regUsername" 
              type="text" 
              :placeholder="t('login_username_placeholder')"
              required
            />
          </div>
          
          <div class="form-group">
            <label for="reg-email">{{ t('register_email') }}</label>
            <input 
              id="reg-email"
              v-model="regEmail" 
              type="email" 
              :placeholder="t('register_email_placeholder')"
              required
            />
          </div>
          
          <div class="form-group">
            <label for="reg-password">{{ t('login_password') }}</label>
            <input 
              id="reg-password"
              v-model="regPassword" 
              type="password" 
              :placeholder="t('login_password_placeholder')"
              required
            />
          </div>
          
          <div v-if="regError" class="error-message">
            {{ regError }}
          </div>
          
          <button type="submit" class="btn-login" :disabled="regLoading">
            {{ regLoading ? t('register_submitting') : t('register_submit') }}
          </button>
          
          <button type="button" class="btn-cancel" @click="showRegister = false">
            {{ t('register_cancel') }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authApi } from '@/api'
import { getPreferredHomePath, loadUserPreferences } from '@/composables/useUserPreferences'
import { useLocale } from '@/composables/useLocale'

const router = useRouter()
const route = useRoute()
const { t } = useLocale()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const showRegister = ref(false)
const regUsername = ref('')
const regEmail = ref('')
const regPassword = ref('')
const regLoading = ref(false)
const regError = ref('')

const handleLogin = async () => {
  error.value = ''
  loading.value = true
  
  try {
    const response = await authApi.login(username.value, password.value)
    authApi.setToken(response.access_token, response.refresh_token)
    await loadUserPreferences(true)
    
    const redirect = route.query.redirect as string || getPreferredHomePath()
    router.push(redirect)
  } catch (e: any) {
    error.value = e.response?.data?.detail || t('login_error_default')
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  regError.value = ''
  regLoading.value = true
  
  try {
    await authApi.register(regUsername.value, regEmail.value, regPassword.value)
    showRegister.value = false
    username.value = regUsername.value
    password.value = regPassword.value
    window.alert(t('register_success'))
  } catch (e: any) {
    regError.value = e.response?.data?.detail || t('register_error_default')
  } finally {
    regLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: rgba(26, 26, 26, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 40px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;

  h1 {
    margin: 0;
    font-size: 32px;
    font-weight: 700;
    color: #fff;
  }

  p {
    margin: 8px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.login-form {
  .form-group {
    margin-bottom: 20px;

    label {
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.8);
    }

    input {
      width: 100%;
      padding: 12px 16px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      color: #fff;
      font-size: 14px;
      transition: all 0.2s;

      &:focus {
        outline: none;
        border-color: #2962FF;
        background: rgba(255, 255, 255, 0.08);
      }

      &::placeholder {
        color: rgba(255, 255, 255, 0.3);
      }
    }
  }

  .error-message {
    padding: 12px;
    background: rgba(255, 23, 68, 0.1);
    border: 1px solid rgba(255, 23, 68, 0.3);
    border-radius: 8px;
    color: #FF1744;
    font-size: 14px;
    margin-bottom: 20px;
  }

  .btn-login {
    width: 100%;
    padding: 14px;
    background: #2962FF;
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: #1E53E5;
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  .btn-cancel {
    width: 100%;
    padding: 14px;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.7);
    font-size: 16px;
    cursor: pointer;
    margin-top: 12px;
    transition: all 0.2s;

    &:hover {
      background: rgba(255, 255, 255, 0.05);
    }
  }
}

.login-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);

  a {
    color: #2962FF;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: rgba(26, 26, 26, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 32px;
  width: 100%;
  max-width: 400px;
  margin: 20px;

  h2 {
    margin: 0 0 24px;
    color: #fff;
    text-align: center;
  }
}
</style>
