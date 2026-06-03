import api from './axios'

export const login = async (username, password) => {
  const response = await api.post('/api/auth/login', { username, password })
  return response.data
}

export const register = async (username, password) => {
  const response = await api.post('/api/auth/register', { username, password })
  return response.data
}
