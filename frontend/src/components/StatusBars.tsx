import { useEffect, useMemo, useState } from 'react'

import { getHealthStatus, getSimulatorStatus, type SimulatorStatus } from '../api'

interface StatusBarsProps {
  cpId: string
  refreshToken: number
}

interface StatusItem {
  connected: boolean
  label: string
  description: string
  badge: string
  timestampLabel: string
  timestamp?: string | null
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

export function StatusBars({ cpId, refreshToken }: StatusBarsProps): JSX.Element {
  const [csConnected, setCsConnected] = useState(false)
  const [csCheckedAt, setCsCheckedAt] = useState<string | null>(null)
  const [cpStatus, setCpStatus] = useState<SimulatorStatus | null>(null)
  const [cpCheckedAt, setCpCheckedAt] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    const fetchStatus = async (): Promise<void> => {
      const [cs, cp] = await Promise.allSettled([
        getHealthStatus(),
        getSimulatorStatus(cpId.trim() || 'CP_1'),
      ])

      if (!isMounted) {
        return
      }

      if (cs.status === 'fulfilled') {
        setCsConnected(cs.value)
        setCsCheckedAt(new Date().toISOString())
      }

      if (cp.status === 'fulfilled') {
        setCpStatus(cp.value)
        setCpCheckedAt(new Date().toISOString())
      } else {
        setCpStatus(null)
        setCpCheckedAt(new Date().toISOString())
      }
    }

    void fetchStatus()
    const interval = window.setInterval(fetchStatus, 5000)
    return () => {
      isMounted = false
      window.clearInterval(interval)
    }
  }, [cpId, refreshToken])

  const items = useMemo<StatusItem[]>(() => {
    return [
      {
        connected: csConnected,
        label: 'Central System',
        description: 'WebSocket Listener :9000',
        badge: csConnected ? 'Online' : 'Offline',
        timestampLabel: 'Letzte Prüfung',
        timestamp: csCheckedAt,
      },
      {
        connected: Boolean(cpStatus?.connected),
        label: `Charge Point ${cpId || 'CP_1'}`,
        description: cpStatus?.connected ? 'OCPP verbunden' : 'Keine aktive Verbindung',
        badge: cpStatus?.connected ? 'Verbunden' : 'Getrennt',
        timestampLabel: 'Letztes Ereignis',
        timestamp: cpStatus?.lastEventTs ?? cpCheckedAt,
      },
    ]
  }, [cpCheckedAt, cpId, cpStatus, csCheckedAt, csConnected])

  return (
    <section className="status-bars" aria-label="Systemstatus">
      {items.map((item) => (
        <article key={item.label} className="status-bar">
          <div className="status-bar__header">
            <span>{item.label}</span>
            <span
              className={`status-indicator ${item.connected ? 'status-indicator--online' : 'status-indicator--offline'}`}
            >
              {item.badge}
            </span>
          </div>
          <p className="status-bar__meta">{item.description}</p>
          <p className="status-bar__timestamp">
            {item.timestampLabel}: {formatTimestamp(item.timestamp ?? null)}
          </p>
        </article>
      ))}
    </section>
  )
}
