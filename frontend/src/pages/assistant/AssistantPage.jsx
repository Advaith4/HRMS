import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowUp,
  Bot,
  Clock,
  Copy,
  FileSearch,
  Loader2,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { sendRagChatMessage } from '../../api'
import { useAuthStore } from '../../store/authStore'

const HR_PROMPTS = [
  'Which candidates are strongest for this role?',
  'Summarize interview performance.',
  'What skills are common among applicants?',
  'Compare shortlisted candidates.',
  'What hiring risks should I be aware of?',
]

const CANDIDATE_PROMPTS = [
  'What is my application status?',
  'What skills should I improve?',
  'Explain my interview feedback.',
  'What does this role require?',
  'What company policies should I know?',
]

const MODE_CONFIG = {
  hr: {
    title: 'HR Copilot',
    eyebrow: 'Talent Intelligence',
    description: 'Ask grounded questions across jobs, candidates, interviews, and company knowledge.',
    accent: 'text-brand-indigo',
    prompts: HR_PROMPTS,
    icon: ShieldCheck,
    placeholder: 'Ask about candidates, interviews, jobs, policies...',
  },
  candidate: {
    title: 'Career Assistant',
    eyebrow: 'Candidate Guidance',
    description: 'Get role-aware guidance from your applications, feedback, role requirements, and policies.',
    accent: 'text-success-primary',
    prompts: CANDIDATE_PROMPTS,
    icon: UserRound,
    placeholder: 'Ask about your applications, feedback, skills, policies...',
  },
}

const formatTime = (date) =>
  new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)

const createMessageId = () => {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const getErrorMessage = (error) => {
  if (error?.code === 'ECONNABORTED') {
    return 'The assistant took too long to respond. Please try again with a shorter question.'
  }
  if (!error?.response) {
    return 'The assistant is unreachable right now. Check your connection and try again.'
  }
  if (error.response.status === 401) {
    return 'Your session has expired. Please sign in again.'
  }
  if (error.response.status === 403) {
    return 'You do not have access to that assistant or knowledge scope.'
  }
  if (error.response.status >= 500) {
    return 'The knowledge service hit an internal error. Please try again shortly.'
  }
  return error.response.data?.detail || 'The assistant could not complete that request.'
}

const sourceName = (source) => {
  if (source.filename) return source.filename
  if (source.source) return source.source
  if (source.entity_type && source.entity_id) return `${source.entity_type} ${source.entity_id}`
  if (source.source_collection) return source.source_collection
  return 'Knowledge source'
}

const relevanceLabel = (distance) => {
  if (typeof distance !== 'number') return null
  const score = Math.max(0, Math.min(100, Math.round((1 - distance) * 100)))
  return `${score}% relevance`
}

const parseInlineCode = (text) => {
  const parts = String(text).split(/(`[^`]+`)/g)
  return parts.map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={index} className="rounded bg-bg-page border border-border-custom px-1 py-0.5 text-[12px] font-mono text-txt-primary">
          {part.slice(1, -1)}
        </code>
      )
    }
    return <React.Fragment key={index}>{part}</React.Fragment>
  })
}

const MarkdownMessage = ({ content }) => {
  const blocks = useMemo(() => {
    const lines = String(content || '').split('\n')
    const parsed = []
    let paragraph = []
    let code = []
    let inCode = false

    const flushParagraph = () => {
      if (paragraph.length) {
        parsed.push({ type: 'paragraph', text: paragraph.join(' ') })
        paragraph = []
      }
    }

    lines.forEach((line) => {
      if (line.trim().startsWith('```')) {
        if (inCode) {
          parsed.push({ type: 'code', text: code.join('\n') })
          code = []
          inCode = false
        } else {
          flushParagraph()
          inCode = true
        }
        return
      }

      if (inCode) {
        code.push(line)
        return
      }

      if (!line.trim()) {
        flushParagraph()
        return
      }

      if (/^\s*[-*]\s+/.test(line)) {
        flushParagraph()
        parsed.push({ type: 'bullet', text: line.replace(/^\s*[-*]\s+/, '') })
        return
      }

      if (/^\s*\d+\.\s+/.test(line)) {
        flushParagraph()
        parsed.push({ type: 'numbered', text: line.replace(/^\s*\d+\.\s+/, '') })
        return
      }

      paragraph.push(line.trim())
    })

    flushParagraph()
    if (code.length) parsed.push({ type: 'code', text: code.join('\n') })
    return parsed
  }, [content])

  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {blocks.map((block, index) => {
        if (block.type === 'code') {
          return (
            <pre key={index} className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">
              <code>{block.text}</code>
            </pre>
          )
        }
        if (block.type === 'bullet') {
          return (
            <div key={index} className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 rounded-full bg-brand-indigo shrink-0" />
              <p>{parseInlineCode(block.text)}</p>
            </div>
          )
        }
        if (block.type === 'numbered') {
          return (
            <div key={index} className="flex gap-2">
              <span className="text-xs font-semibold text-txt-tertiary">{index + 1}.</span>
              <p>{parseInlineCode(block.text)}</p>
            </div>
          )
        }
        return <p key={index}>{parseInlineCode(block.text)}</p>
      })}
    </div>
  )
}

const SourceList = ({ sources }) => {
  if (!sources?.length) return null
  return (
    <div className="mt-4 border-t border-border-custom pt-3">
      <div className="mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-txt-tertiary">
        <FileSearch size={13} />
        Sources Used
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {sources.map((source, index) => {
          const relevance = relevanceLabel(source.distance)
          return (
            <div key={`${source.collection}-${sourceName(source)}-${index}`} className="rounded-lg border border-border-custom bg-bg-page px-3 py-2">
              <div className="flex items-start justify-between gap-3 min-w-0 w-full">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-semibold text-txt-primary">{sourceName(source)}</p>
                  <p className="mt-0.5 truncate text-[11px] text-txt-tertiary">{source.collection || 'collection unavailable'}</p>
                </div>
                {relevance && (
                  <span className="shrink-0 rounded-full border border-brand-indigo/20 bg-brand-indigo-muted px-2 py-0.5 text-[10px] font-semibold text-brand-indigo">
                    {relevance}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-indigo text-white">
          <Bot size={16} />
        </div>
      )}
      <div className={`max-w-[min(780px,100%)] rounded-lg border px-4 py-3 shadow-xs ${
        isUser
          ? 'border-brand-indigo bg-brand-indigo text-white'
          : 'border-border-custom bg-white text-txt-primary'
      }`}>
        <div className="mb-2 flex items-center justify-between gap-4">
          <span className={`text-[11px] font-bold uppercase tracking-wider ${isUser ? 'text-white/80' : 'text-txt-tertiary'}`}>
            {isUser ? 'You' : 'Assistant'}
          </span>
          <span className={`inline-flex items-center gap-1 text-[10px] ${isUser ? 'text-white/70' : 'text-txt-tertiary'}`}>
            <Clock size={11} />
            {message.time}
          </span>
        </div>
        <MarkdownMessage content={message.content} />
        {!isUser && <SourceList sources={message.sources} />}
      </div>
    </div>
  )
}

export const AssistantPage = ({ mode = 'hr' }) => {
  const config = MODE_CONFIG[mode] || MODE_CONFIG.hr
  const ModeIcon = config.icon
  const { user } = useAuthStore()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isSubmitting])

  const submitQuery = async (queryText) => {
    const query = queryText.trim()
    if (!query || isSubmitting) return

    const userMessage = {
      id: createMessageId(),
      role: 'user',
      content: query,
      time: formatTime(new Date()),
    }

    setMessages((current) => [...current, userMessage])
    setInput('')
    setError('')
    setIsSubmitting(true)

    try {
      const response = await sendRagChatMessage(query)
      const answer = response?.answer?.trim() || 'I could not find a useful answer for that question.'
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: 'assistant',
          content: answer,
          sources: response?.sources || [],
          collectionsUsed: response?.collections_used || [],
          time: formatTime(new Date()),
        },
      ])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsSubmitting(false)
      textareaRef.current?.focus()
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    submitQuery(input)
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submitQuery(input)
    }
  }

  const copyLastAnswer = async () => {
    const lastAnswer = [...messages].reverse().find((message) => message.role === 'assistant')
    if (!lastAnswer?.content) return
    try {
      await navigator.clipboard.writeText(lastAnswer.content)
    } catch (err) {
      console.warn('assistant_copy_failed', err)
    }
  }

  return (
    <div className="flex h-[calc(100vh-10.5rem)] md:h-[calc(100vh-6.5rem)] min-h-[400px] md:min-h-[640px] flex-col gap-4 text-txt-primary w-full min-w-0">
      <div className="flex flex-col justify-between gap-3 border-b border-border-custom pb-4 md:flex-row md:items-end">
        <div className="min-w-0">
          <div className="mb-2 inline-flex items-center gap-2 rounded-lg border border-border-custom bg-white px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider text-txt-tertiary">
            <ModeIcon size={14} className={config.accent} />
            {config.eyebrow}
          </div>
          <h2 className="text-xl font-bold tracking-tight text-txt-primary">{config.title}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-txt-secondary">{config.description}</p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-border-custom bg-white px-3 py-2 text-xs text-txt-secondary">
          <Sparkles size={15} className={config.accent} />
          <span className="truncate">Signed in as {user?.username || 'user'}</span>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)] w-full min-w-0">
        <aside className="flex min-h-0 flex-col gap-3 rounded-lg border border-border-custom bg-white p-4 shadow-xs w-full min-w-0">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-txt-secondary">Suggested Prompts</h3>
            <p className="mt-1 text-xs leading-relaxed text-txt-tertiary">Use these to start a grounded session.</p>
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:flex lg:flex-col lg:gap-2">
            {config.prompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => submitQuery(prompt)}
                disabled={isSubmitting}
                className="w-full min-w-0 rounded-lg border border-border-custom bg-bg-page px-3 py-2 text-left text-xs font-medium text-txt-secondary transition-colors hover:border-brand-indigo/30 hover:bg-brand-indigo-muted/40 hover:text-txt-primary disabled:cursor-not-allowed disabled:opacity-60"
              >
                {prompt}
              </button>
            ))}
          </div>
        </aside>

        <section className="flex min-h-0 flex-col rounded-lg border border-border-custom bg-white shadow-xs w-full min-w-0">
          <div className="flex items-center justify-between border-b border-border-custom px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-indigo text-white">
                <MessageSquare size={16} />
              </div>
              <div>
                <p className="text-sm font-semibold text-txt-primary">Conversation</p>
                <p className="text-[11px] text-txt-tertiary">Frontend session history</p>
              </div>
            </div>
            <button
              type="button"
              onClick={copyLastAnswer}
              disabled={!messages.some((message) => message.role === 'assistant')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border-custom bg-bg-page px-3 py-1.5 text-xs font-semibold text-txt-secondary transition-colors hover:bg-bg-elevated disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Copy size={13} />
              Copy
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto bg-bg-page/40 px-4 py-5">
            {messages.length === 0 ? (
              <div className="flex h-full min-h-[340px] items-center justify-center">
                <div className="max-w-md rounded-lg border border-dashed border-border-custom bg-white p-6 text-center">
                  <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-indigo-muted text-brand-indigo">
                    <Bot size={20} />
                  </div>
                  <h3 className="text-sm font-bold text-txt-primary">Start with a focused question</h3>
                  <p className="mt-2 text-xs leading-relaxed text-txt-secondary">
                    Answers are grounded in authorized TalentForge knowledge and include the sources used.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}
                {isSubmitting && (
                  <div className="flex gap-3">
                    <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-indigo text-white">
                      <Bot size={16} />
                    </div>
                    <div className="rounded-lg border border-border-custom bg-white px-4 py-3 text-sm text-txt-secondary shadow-xs">
                      <span className="inline-flex items-center gap-2">
                        <Loader2 size={15} className="animate-spin text-brand-indigo" />
                        Searching authorized knowledge...
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {error && (
            <div className="border-t border-danger-primary/20 bg-danger-bg/20 px-4 py-3">
              <div className="flex items-start gap-2 text-sm text-danger-primary">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="border-t border-border-custom bg-white p-3">
            <label htmlFor="assistant-query" className="sr-only">Assistant query</label>
            <div className="flex items-end gap-2 rounded-lg border border-border-custom bg-bg-page p-2 focus-within:border-brand-indigo/40 focus-within:ring-2 focus-within:ring-brand-indigo/10">
              <textarea
                id="assistant-query"
                ref={textareaRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={config.placeholder}
                rows={2}
                maxLength={4000}
                disabled={isSubmitting}
                className="max-h-32 min-h-[44px] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-txt-primary outline-none placeholder:text-txt-tertiary disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={isSubmitting || !input.trim()}
                aria-label="Send message"
                aria-busy={isSubmitting}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-indigo text-white transition-colors hover:bg-brand-indigo-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? <Loader2 size={17} className="animate-spin" /> : <ArrowUp size={17} />}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  )
}

export default AssistantPage
