import api from './axios'

export const getPromotions = async (employeeId) => {
  const response = await api.get(`/api/promotions/employee/${employeeId}`)
  return response.data
}

export const addPromotion = async (employeeId, data) => {
  // data: { new_designation, promotion_date, reason }
  const response = await api.post(`/api/promotions/employee/${employeeId}`, data)
  return response.data
}

export const getRecentPromotions = async () => {
  const response = await api.get('/api/promotions/recent')
  return response.data
}
