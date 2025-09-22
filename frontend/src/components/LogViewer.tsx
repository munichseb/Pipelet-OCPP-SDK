import { useEffect, useMemo, useRef, useState } from 'react'

import {
  apiClient,
  downloadLogs,
  fetchLogs,
  getErrorMessage,
  type LogEntry,
  type LogSource,
} from '../api'

interface LogViewerStatus {
  type: 'success' | 'error'
  text: string
}

type StreamState = 'connecting' | 'open' | 'error'

const SOURCE_OPTIONS: Array<{ value: LogSource | 'all'; label: string }> = [
  { value: 'all', label: 'Alle Quellen' },
  { value: 'cs', label: 'Central System' },
  { value: 'cp', label: 'Charge Point' },
  { value: 'pipelet', label: 'Pipelets' },
]

export function LogViewer(): JSX.Element {
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [source, setSource] = useState<LogSource | 'all'>('all')
  const [limit, setLimit] = useState(200)
  const [autoScroll, setAutoScroll] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [status, setStatus] = useState<LogViewerStatus | null>(null)
  const [streamState, setStreamState] = useState<StreamState>('connecting')
  const [isDownloading, setIsDownloading] = useState(false)
  const logContainerRef = useRef<HTMLDivElement | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const effectiveLimit = Math.max(20, Math.min(limit, 1000))

  useEffect(() => {
    let cancelled = false
    const loadInitial = async (): Promise<void> => {
      try {
        const logs = await fetchLogs({
          source: source === 'all' ? undefined : source,
          limit: effectiveLimit,
        })
        if (cancelled) {
          return
        }
        const ordered = [...logs].reverse()
        setEntries(ordered.slice(-effectiveLimit))
      } catch (error) {
        if (!cancelled) {
          setStatus({ type: 'error', text: getErrorMessage(error) })
        }
      }
    }

    void loadInitial()
    return () => {
      cancelled = true
    }
  }, [source, effectiveLimit])

  useEffect(() => {
    setEntries((prev) => {
      if (prev.length <= effectiveLimit) {
        return prev
      }
      return prev.slice(prev.length - effectiveLimit)
    })
  }, [effectiveLimit])

  useEffect(() => {
    const base = apiClient.defaults.baseURL?.replace(/\/?$/, '') ?? ''
    const params = new URLSearchParams()
    if (source !== 'all') {
      params.set('source', source)
    }
    const url = `${base}/api/logs/stream${params.toString() ? `?${params.toString()}` : ''}`

    setStreamState('connecting')
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }

    const eventSource = new EventSource(url)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setStreamState('open')
    }

    eventSource.onerror = () => {
      setStreamState('error')
    }

    eventSource.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data) as Record<string, unknown>
        const payload: LogEntry = {
          id: Number(raw.id ?? 0),
          source: ((raw.source as LogSource) ?? 'pipelet') as LogSource,
          message: String(raw.message ?? ''),
          createdAt: String(raw.createdAt ?? ''),
        }
        setEntries((prev) => {
          const exists = prev.some((entry) => entry.id === payload.id)
          const next = exists
            ? prev.map((entry) => (entry.id === payload.id ? payload : entry))
            : [...prev, payload]
          if (next.length > effectiveLimit) {
            return next.slice(next.length - effectiveLimit)
          }
          return next
        })
      } catch (error) {
        setStatus({ type: 'error', text: getErrorMessage(error) })
      }
    }

    return () => {
      eventSource.close()
      eventSourceRef.current = null
    }
  }, [effectiveLimit, source])

  useEffect(() => {
    if (!status) {
      return
    }
    const timeout = window.setTimeout(() => setStatus(null), 4000)
    return () => window.clearTimeout(timeout)
  }, [status])

  useEffect(() => {
    if (!autoScroll) {
      return
    }
    const container = logContainerRef.current
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  }, [autoScroll, entries])

  const filteredEntries = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    if (!query) {
      return entries
    }
    return entries.filter(
      (entry) =>
        entry.message.toLowerCase().includes(query) ||
        entry.source.toLowerCase().includes(query) ||
        entry.createdAt.toLowerCase().includes(query),
    )
  }, [entries, searchTerm])

  const handleLimitChange = (value: number) => {
    if (Number.isNaN(value)) {
      return
    }
    setLimit(Math.max(20, Math.min(value, 1000)))
  }

  const handleClear = () => {
    setEntries([])
  }

  const handleDownload = async () => {
    setIsDownloading(true)
    try {
      const blob = await downloadLogs(source, effectiveLimit)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const suffix = source === 'all' ? 'all' : source
      link.download = `pipelet-logs-${suffix}-${Date.now()}.ndjson`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      setStatus({ type: 'success', text: 'Log-Download gestartet' })
    } catch (error) {
      setStatus({ type: 'error', text: getErrorMessage(error) })
    } finally {
      setIsDownloading(false)
    }
  }

  const highlight = (text: string) => {
    const query = searchTerm.trim()
    if (!query) {
      return text
    }
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const regex = new RegExp(`(${escaped})`, 'gi')
    return text.split(regex).map((part, index) => {
      if (!part) {
        return null
      }
      const isMatch = part.toLowerCase() === query.toLowerCase()
      return isMatch ? (
        <mark key={`${part}-${index}`} className="log-viewer__highlight">
          {part}
        </mark>
      ) : (
        <span key={`${part}-${index}`}>{part}</span>
      )
    })
  }

  return (
    <section className="log-viewer" aria-label="Live-Logs">
      <header className="log-viewer__header">
        <h2>Live-Logs</h2>
        <span className={`log-viewer__stream log-viewer__stream--${streamState}`}>
          {streamState === 'open'
            ? 'Streaming aktiv'
            : streamState === 'connecting'
              ? 'Verbindung wird aufgebaut…'
              : 'Stream getrennt'}
        </span>
      </header>

      <div className="log-viewer__controls">
        <label className="log-viewer__field">
          <span>Quelle</span>
          <select value={source} onChange={(event) => setSource(event.target.value as LogSource | 'all')}>
            {SOURCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="log-viewer__field">
          <span>Nur letzte N</span>
          <input
            type="number"
            value={effectiveLimit}
            min={20}
            max={1000}
            onChange={(event) => handleLimitChange(Number(event.target.value))}
          />
        </label>

        <label className="log-viewer__field log-viewer__field--search">
          <span>Suche</span>
          <input
            type="text"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="contains:text"
            autoComplete="off"
          />
        </label>

        <label className="log-viewer__toggle">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(event) => setAutoScroll(event.target.checked)}
          />
          Auto-Scroll
        </label>
      </div>

      <div className="log-viewer__entries" ref={logContainerRef}>
        {filteredEntries.length === 0 ? (
          <p className="log-viewer__empty">Keine Logeinträge gefunden</p>
        ) : (
          filteredEntries.map((entry) => (
            <article key={entry.id} className="log-viewer__entry">
              <header>
                <span className={`log-viewer__badge log-viewer__badge--${entry.source}`}>
                  {entry.source.toUpperCase()}
                </span>
                <time dateTime={entry.createdAt}>{entry.createdAt}</time>
              </header>
              <p>{highlight(entry.message)}</p>
            </article>
          ))
        )}
      </div>

      <footer className="log-viewer__actions">
        <button type="button" onClick={handleClear}>
          Clear
        </button>
        <button type="button" onClick={handleDownload} disabled={isDownloading}>
          {isDownloading ? 'Download…' : 'Download'}
        </button>
      </footer>

      {status && (
        <div className={`status-message status-message--${status.type}`} role="status">
          {status.text}
        </div>
      )}
    </section>
  )
}
