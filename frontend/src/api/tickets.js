import api from './axios'

export const createTicket = async (data) => {
  // data: { title, description, category, priority }
  const response = await api.post('/api/tickets', data)
  return response.data
}

export const listTickets = async () => {
  const response = await api.get('/api/tickets')
  return response.data
}

export const assignTicket = async (id, assignedTo) => {
  const response = await api.put(`/api/tickets/${id}/assign`, { assigned_to: assignedTo })
  return response.data
}

export const updateTicketStatus = async (id, status, resolutionNote) => {
  const response = await api.put(`/api/tickets/${id}/status`, { status, resolution_note: resolutionNote })
  return response.data
}
