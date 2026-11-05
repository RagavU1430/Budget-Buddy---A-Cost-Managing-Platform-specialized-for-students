import api from './client'

export const getNotifications = (params = {}) => api.get('/notifications/', { params });
export const markAllRead = () => api.post('/notifications/mark-all-read/');
export const getUnreadCount = () => api.get('/notifications/unread-count/');
export const markNotificationRead = (id) => api.patch(`/notifications/${id}/`, { is_read: true });
export const deleteNotification = (id) => api.delete(`/notifications/${id}/`);
