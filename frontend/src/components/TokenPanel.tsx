import { useEffect, useState } from 'react'

import {
  createApiToken,
  getApiToken,
  getApiProtectionStatus,
  getErrorMessage,
  listApiTokens,
  revokeApiToken,
  setApiToken,
  setApiProtectionStatus,
  type ApiTokenInfo,
  type ApiTokenRole,
} from '../api'

interface TokenModalState {
  name: string
  token: string
}

const ROLE_LABELS: Record<ApiTokenRole, string> = {
  admin: 'Admin',
  readonly: 'Read-Only',
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return '—'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function maskToken(value: string | null): string {
  if (!value) {
    return 'Kein Token gespeichert'
  }
  if (value.length <= 12) {
    return value
  }
  return `${value.slice(0, 6)}…${value.slice(-4)}`
}

const TOKEN_PANEL_COLLAPSE_STORAGE_KEY = 'pipelet.ui.tokenPanel.collapsed'

export function TokenPanel(): JSX.Element {
  const [tokens, setTokens] = useState<ApiTokenInfo[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)
  const [newTokenName, setNewTokenName] = useState('')
  const [newTokenRole, setNewTokenRole] = useState<ApiTokenRole>('readonly')
  const [modal, setModal] = useState<TokenModalState | null>(null)
  const [activeTokenInput, setActiveTokenInput] = useState(getApiToken() ?? '')
  const [isProtectionEnabled, setIsProtectionEnabled] = useState(false)
  const [isProtectionLoading, setIsProtectionLoading] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(true)

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    try {
      const stored = window.localStorage.getItem(TOKEN_PANEL_COLLAPSE_STORAGE_KEY)
      if (stored !== null) {
        setIsCollapsed(stored !== 'false')
      }
    } catch (err) {
      console.warn('Konnte Token-Panel-Zustand nicht laden', err)
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    try {
      window.localStorage.setItem(
        TOKEN_PANEL_COLLAPSE_STORAGE_KEY,
        isCollapsed ? 'true' : 'false',
      )
    } catch (err) {
      console.warn('Konnte Token-Panel-Zustand nicht speichern', err)
    }
  }, [isCollapsed])

  const maskedActiveToken = maskToken(getApiToken())
  const collapseIcon = isCollapsed ? '▼' : '▲'
  const panelContentId = 'api-token-panel-content'

  useEffect(() => {
    let mounted = true
    const load = async (): Promise<void> => {
      setIsLoading(true)
      try {
        const items = await listApiTokens()
        if (mounted) {
          setTokens(items)
        }
      } catch (err) {
        if (mounted) {
          setError(getErrorMessage(err))
        }
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }
    void load()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true
    const loadProtection = async (): Promise<void> => {
      setIsProtectionLoading(true)
      try {
        const status = await getApiProtectionStatus()
        if (mounted) {
          setIsProtectionEnabled(status.enabled)
        }
      } catch (err) {
        if (mounted) {
          setError(getErrorMessage(err))
        }
      } finally {
        if (mounted) {
          setIsProtectionLoading(false)
        }
      }
    }

    void loadProtection()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!status) {
      return
    }
    const timeout = window.setTimeout(() => setStatus(null), 3000)
    return () => window.clearTimeout(timeout)
  }, [status])

  const refreshTokens = async (): Promise<void> => {
    try {
      const items = await listApiTokens()
      setTokens(items)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleCreateToken = async (): Promise<void> => {
    const name = newTokenName.trim()
    if (!name) {
      setError('Name für das Token angeben')
      return
    }
    try {
      setError(null)
      const created = await createApiToken({ name, role: newTokenRole })
      setModal({ name: created.name, token: created.token })
      setNewTokenName('')
      await refreshTokens()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleRevoke = async (tokenId: number): Promise<void> => {
    try {
      await revokeApiToken(tokenId)
      setStatus('Token deaktiviert')
      await refreshTokens()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleActiveTokenSave = (): void => {
    setApiToken(activeTokenInput)
    setStatus(activeTokenInput.trim() ? 'Token gespeichert' : 'Token entfernt')
  }

  const handleUseCreatedToken = (): void => {
    if (modal) {
      setApiToken(modal.token)
      setActiveTokenInput(modal.token)
      setStatus('Token übernommen und gespeichert')
      setModal(null)
    }
  }

  const handleProtectionToggle = async (): Promise<void> => {
    const nextValue = !isProtectionEnabled
    setIsProtectionLoading(true)
    try {
      setError(null)
      const updated = await setApiProtectionStatus(nextValue)
      setIsProtectionEnabled(updated.enabled)
      setStatus(
        updated.enabled
          ? 'API-Zugriffsschutz aktiviert'
          : 'API-Zugriffsschutz deaktiviert',
      )
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsProtectionLoading(false)
    }
  }

  const handleModalClose = (): void => {
    setModal(null)
  }

  return (
    <section
      className={`token-panel${isCollapsed ? ' token-panel--collapsed' : ''}`}
      aria-label="API Token Verwaltung"
    >
      <div className="token-panel__header">
        <div className="token-panel__protection">
          <button
            type="button"
            role="switch"
            aria-checked={isProtectionEnabled}
            aria-label="API Zugriffsschutz umschalten"
            onClick={() => void handleProtectionToggle()}
            className={`token-panel__toggle${isProtectionEnabled ? ' token-panel__toggle--on' : ''}`}
            disabled={isProtectionLoading}
          >
            <span className="token-panel__toggle-thumb" aria-hidden="true" />
          </button>
          <div className="token-panel__protection-text">
            <span className="token-panel__protection-label">Zugriffsschutz</span>
            <span
              className={`token-panel__protection-state${
                isProtectionEnabled ? ' token-panel__protection-state--on' : ''
              }`}
            >
              {isProtectionEnabled ? 'An' : 'Aus'}
            </span>
          </div>
        </div>
        <h2 className="token-panel__title">API Tokens</h2>
        <div className="token-panel__header-actions">
          <button
            type="button"
            className="token-panel__collapse-button"
            aria-expanded={!isCollapsed}
            aria-controls={panelContentId}
            aria-label={
              isCollapsed
                ? 'API Tokens anzeigen'
                : 'API Tokens verbergen'
            }
            onClick={() => setIsCollapsed((value) => !value)}
          >
            <span aria-hidden="true">{collapseIcon}</span>
          </button>
          <button type="button" onClick={() => void refreshTokens()} disabled={isLoading}>
            Aktualisieren
          </button>
        </div>
      </div>
      <div
        id={panelContentId}
        className="token-panel__content"
        hidden={isCollapsed}
      >
        {status && <div className="token-panel__status token-panel__status--success">{status}</div>}
        {error && <div className="token-panel__status token-panel__status--error">{error}</div>}

        <div className="token-panel__section">
          <label className="token-panel__label" htmlFor="active-token-input">
            Aktives Token
          </label>
          <input
            id="active-token-input"
            type="text"
            value={activeTokenInput}
            onChange={(event) => setActiveTokenInput(event.target.value)}
            placeholder="Token einfügen"
          />
          <div className="token-panel__actions">
            <button type="button" onClick={handleActiveTokenSave}>
              Speichern
            </button>
            <button
              type="button"
              className="token-panel__button-secondary"
              onClick={() => {
                setActiveTokenInput('')
                setApiToken(null)
                setStatus('Token entfernt')
              }}
            >
              Entfernen
            </button>
          </div>
          <p className="token-panel__hint">Aktuell: {maskedActiveToken}</p>
        </div>

        <div className="token-panel__section">
          <h3>Neues Token</h3>
          <div className="token-panel__form">
            <label htmlFor="token-name">Name</label>
            <input
              id="token-name"
              type="text"
              value={newTokenName}
              onChange={(event) => setNewTokenName(event.target.value)}
              placeholder="z. B. Deployment"
            />
            <label htmlFor="token-role">Rolle</label>
            <select
              id="token-role"
              value={newTokenRole}
              onChange={(event) => setNewTokenRole(event.target.value as ApiTokenRole)}
            >
              <option value="readonly">Read-Only</option>
              <option value="admin">Admin</option>
            </select>
            <button type="button" onClick={handleCreateToken} disabled={isLoading}>
              Neues Token erstellen
            </button>
          </div>
        </div>

        <div className="token-panel__section">
          <h3>Vorhandene Tokens</h3>
          <div className="token-table-wrapper">
            <table className="token-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Rolle</th>
                  <th>Erstellt</th>
                  <th>Status</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {tokens.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="token-table__empty">
                      Keine Tokens vorhanden
                    </td>
                  </tr>
                ) : (
                  tokens.map((token) => (
                    <tr key={token.id}>
                      <td>{token.name}</td>
                      <td>{ROLE_LABELS[token.role]}</td>
                      <td>{formatTimestamp(token.created_at)}</td>
                      <td>
                        {token.revoked_at
                          ? `Revoked (${formatTimestamp(token.revoked_at)})`
                          : 'Aktiv'}
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() => handleRevoke(token.id)}
                          disabled={Boolean(token.revoked_at)}
                        >
                          Deaktivieren
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {modal && (
        <div className="token-modal" role="dialog" aria-modal="true">
          <div className="token-modal__content">
            <h3>Neues Token erstellt</h3>
            <p>
              Das Token <strong>{modal.name}</strong> wird nur einmal angezeigt. Bitte sicher speichern.
            </p>
            <pre className="token-modal__token">{modal.token}</pre>
            <div className="token-modal__actions">
              <button type="button" onClick={handleUseCreatedToken}>
                Als aktives Token verwenden
              </button>
              <button
                type="button"
                className="token-panel__button-secondary"
                onClick={() => {
                  if (navigator.clipboard) {
                    void navigator.clipboard.writeText(modal.token)
                    setStatus('Token in Zwischenablage kopiert')
                  } else {
                    setError('Zwischenablage nicht verfügbar')
                  }
                }}
              >
                Kopieren
              </button>
              <button
                type="button"
                className="token-panel__button-secondary"
                onClick={handleModalClose}
              >
                Schließen
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
