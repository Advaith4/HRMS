import React from 'react'

export const SkeletonCard = ({ mode = 'card', count = 1 }) => {
  const renders = Array.from({ length: count })

  const renderSkeleton = (index) => {
    if (mode === 'metric') {
      return (
        <div key={index} className="rounded-xl border border-border-custom bg-bg-surface p-6 animate-shimmer">
          <div className="h-4 w-24 rounded bg-bg-elevated mb-4" />
          <div className="h-8 w-16 rounded bg-bg-elevated" />
        </div>
      )
    }

    if (mode === 'table') {
      return (
        <div key={index} className="w-full space-y-4 py-4 animate-shimmer">
          <div className="flex space-x-4">
            <div className="h-4 w-12 rounded bg-bg-elevated" />
            <div className="h-4 flex-1 rounded bg-bg-elevated" />
            <div className="h-4 w-24 rounded bg-bg-elevated" />
            <div className="h-4 w-16 rounded bg-bg-elevated" />
          </div>
          <div className="border-t border-border-custom" />
        </div>
      )
    }

    if (mode === 'chart') {
      return (
        <div key={index} className="rounded-xl border border-border-custom bg-bg-surface p-6 animate-shimmer flex flex-col justify-end h-[300px] space-y-4">
          <div className="h-4 w-40 rounded bg-bg-elevated self-start mb-auto" />
          <div className="flex items-end justify-between w-full h-[200px] px-4">
            <div className="h-[40%] w-[10%] rounded-t bg-bg-elevated" />
            <div className="h-[75%] w-[10%] rounded-t bg-bg-elevated" />
            <div className="h-[50%] w-[10%] rounded-t bg-bg-elevated" />
            <div className="h-[90%] w-[10%] rounded-t bg-bg-elevated" />
            <div className="h-[60%] w-[10%] rounded-t bg-bg-elevated" />
            <div className="h-[80%] w-[10%] rounded-t bg-bg-elevated" />
            <div className="h-[30%] w-[10%] rounded-t bg-bg-elevated" />
          </div>
        </div>
      )
    }

    return (
      <div key={index} className="rounded-xl border border-border-custom bg-bg-surface p-6 animate-shimmer space-y-4">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-full bg-bg-elevated" />
          <div className="space-y-2 flex-1">
            <div className="h-4 w-1/3 rounded bg-bg-elevated" />
            <div className="h-3 w-1/4 rounded bg-bg-elevated" />
          </div>
        </div>
        <div className="space-y-2 pt-2">
          <div className="h-3 w-full rounded bg-bg-elevated" />
          <div className="h-3 w-5/6 rounded bg-bg-elevated" />
        </div>
        <div className="h-8 w-24 rounded bg-bg-elevated pt-2" />
      </div>
    )
  }

  return (
    <>
      {renders.map((_, idx) => renderSkeleton(idx))}
    </>
  )
}
export default SkeletonCard
