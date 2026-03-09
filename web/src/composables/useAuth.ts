import { ref, computed } from 'vue'
import { authApi } from '@/api'

const user = ref<any>(null)
const loading = ref(false)

export function useAuth() {
  const isAuthenticated = computed(() => !!authApi.getToken())

  const login = async (username: string, password: string) => {
    loading.value = true
    try {
      const response = await authApi.login(username, password)
      authApi.setToken(response.access_token, response.refresh_token)
      await fetchUser()
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  const logout = () => {
    authApi.removeToken()
    user.value = null
  }

  const fetchUser = async () => {
    if (!authApi.getToken()) return null
    try {
      user.value = await authApi.getMe()
      return user.value
    } catch (error) {
      console.error('Failed to fetch user:', error)
      logout()
      return null
    }
  }

  const checkAuth = async () => {
    if (authApi.getToken()) {
      await fetchUser()
    }
    return isAuthenticated.value
  }

  return {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    fetchUser,
    checkAuth,
  }
}
