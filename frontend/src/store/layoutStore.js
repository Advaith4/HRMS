import { create } from 'zustand'

export const useLayoutStore = create((set) => ({
  isFullscreen: false,
  setFullscreen: (value) => set({ isFullscreen: value })
}))
