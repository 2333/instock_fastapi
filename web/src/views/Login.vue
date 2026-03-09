<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>InStock</h1>
        <p>智能股票分析平台</p>
      </div>
      
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">用户名</label>
          <input 
            id="username"
            v-model="username" 
            type="text" 
            placeholder="请输入用户名"
            required
          />
        </div>
        
        <div class="form-group">
          <label for="password">密码</label>
          <input 
            id="password"
            v-model="password" 
            type="password" 
            placeholder="请输入密码"
            required
          />
        </div>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      
      <div class="login-footer">
        <p>还没有账号? <a href="#" @click.prevent="showRegister = true">立即注册</a></p>
      </div>
    </div>

    <!-- Register Modal -->
    <div v-if="showRegister" class="modal-overlay" @click="showRegister = false">
      <div class="modal-card" @click.stop>
        <h2>注册新账号</h2>
        <form @submit.prevent="handleRegister" class="login-form">
          <div class="form-group">
            <label for="reg-username">用户名</label>
            <input 
              id="reg-username"
              v-model="regUsername" 
              type="text" 
              placeholder="请输入用户名"
              required
            />
          </div>
          
          <div class="form-group">
            <label for="reg-email">邮箱</label>
            <input 
              id="reg-email"
              v-model="regEmail" 
              type="email" 
              placeholder="请输入邮箱"
              required
            />
          </div>
          
          <div class="form-group">
            <label for="reg-password">密码</label>
            <input 
              id="reg-password"
              v-model="regPassword" 
              type="password" 
              placeholder="请输入密码"
              required
            />
          </div>
          
          <div v-if="regError" class="error-message">
            {{ regError }}
          </div>
          
          <button type="submit" class="btn-login" :disabled="regLoading">
            {{ regLoading ? '注册中...' : '注册' }}
          </button>
          
          <button type="button" class="btn-cancel" @click="showRegister = false">
            取消
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

const router = useRouter()
const route = useRoute()

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
    
    const redirect = route.query.redirect as string || '/'
    router.push(redirect)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '登录失败，请检查用户名和密码'
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
    alert('注册成功，请登录')
  } catch (e: any) {
    regError.value = e.response?.data?.detail || '注册失败'
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
