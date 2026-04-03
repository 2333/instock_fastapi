import api from './index'

export const alertApi = {
  // 预警条件 CRUD
  list() {
    return api.get('/alerts/conditions')
  },

  create(data: {
    name: string
    code: string
    condition: { type: string; operator: string; value: number }
    notify_channels?: string[]
  }) {
    return api.post('/alerts/conditions', data)
  },

  get(id: number) {
    return api.get(`/alerts/conditions/${id}`)
  },

  update(id: number, data: Partial<{
    name: string
    condition: any
    is_active: boolean
    notify_channels: string[]
  }>) {
    return api.put(`/alerts/conditions/${id}`, data)
  },

  remove(id: number) {
    return api.delete(`/alerts/conditions/${id}`)
  },

  // 通知
  listNotifications(limit?: number) {
    return api.get('/alerts/notifications', { params: { limit } })
  },

  markRead(notifId: number) {
    return api.patch(`/alerts/notifications/${notifId}/read`)
  },

  getUnreadCount() {
    return api.get('/alerts/unread-count')
  },
}
