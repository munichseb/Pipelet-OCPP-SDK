import { useEffect, useState } from 'react'

import {
  connectSimulator,
  disconnectSimulator,
  getErrorMessage,
  sendSimulatorRfid,
  startSimulatorHeartbeat,
  startSimulatorTransaction,
  stopSimulatorHeartbeat,
  stopSimulatorTransaction,
  type SimulatorState,
} from '../api'

interface SimulatorPanelProps {
  cpId: string
  onCpIdChange: (value: string) => void
  onActionComplete?: () => void
}

interface PanelStatus {
  type: 'success' | 'error'
  text: string
}

export function SimulatorPanel({
  cpId,
  onCpIdChange,
  onActionComplete,
}: SimulatorPanelProps): JSX.Element {
  const [idTag, setIdTag] = useState('TEST_TAG')
  const [heartbeatActive, setHeartbeatActive] = useState(false)
  const [isBusy, setIsBusy] = useState(false)
  const [status, setStatus] = useState<PanelStatus | null>(null)
  const [lastState, setLastState] = useState<SimulatorState | null>(null)

  useEffect(() => {
    if (status === null) {
      return
    }
    const timeout = window.setTimeout(() => setStatus(null), 4000)
    return () => window.clearTimeout(timeout)
  }, [status])

  const executeAction = async (
    action: () => Promise<SimulatorState>,
    successMessage: string,
    afterSuccess?: (state: SimulatorState) => void,
  ): Promise<void> => {
    setIsBusy(true)
    try {
      const state = await action()
      setLastState(state)
      setStatus({ type: 'success', text: successMessage })
      afterSuccess?.(state)
      onActionComplete?.()
    } catch (error) {
      setStatus({ type: 'error', text: getErrorMessage(error) })
    } finally {
      setIsBusy(false)
    }
  }

  const handleConnect = async (): Promise<void> => {
    const trimmed = cpId.trim() || 'CP_1'
    await executeAction(
      () => connectSimulator(trimmed),
      `Charge Point ${trimmed} verbunden`,
      () => {
        setHeartbeatActive(false)
      },
    )
  }

  const handleDisconnect = async (): Promise<void> => {
    const trimmed = cpId.trim() || 'CP_1'
    await executeAction(
      () => disconnectSimulator(trimmed),
      `Charge Point ${trimmed} getrennt`,
      () => {
        setHeartbeatActive(false)
      },
    )
  }

  const handleSendRfid = async (): Promise<void> => {
    const trimmed = cpId.trim() || 'CP_1'
    const tag = idTag.trim() || 'RFID_DEMO'
    await executeAction(
      () => sendSimulatorRfid(trimmed, tag),
      `RFID ${tag} gesendet`,
    )
  }

  const handleStartTransaction = async (): Promise<void> => {
    const trimmed = cpId.trim() || 'CP_1'
    const tag = idTag.trim() || 'RFID_DEMO'
    await executeAction(
      () => startSimulatorTransaction(trimmed, tag),
      'Ladevorgang gestartet',
    )
  }

  const handleStopTransaction = async (): Promise<void> => {
    const trimmed = cpId.trim() || 'CP_1'
    await executeAction(
      () => stopSimulatorTransaction(trimmed),
      'Ladevorgang gestoppt',
      () => {
        setHeartbeatActive(false)
      },
    )
  }

  const handleToggleHeartbeat = async (): Promise<void> => {
    const trimmed = cpId.trim() || 'CP_1'
    if (heartbeatActive) {
      await executeAction(
        () => stopSimulatorHeartbeat(trimmed),
        'Heartbeats gestoppt',
        () => setHeartbeatActive(false),
      )
    } else {
      await executeAction(
        () => startSimulatorHeartbeat(trimmed),
        'Heartbeats gestartet',
        () => setHeartbeatActive(true),
      )
    }
  }

  return (
    <section className="simulator-panel" aria-label="Simulator-Steuerung">
      <header className="simulator-panel__header">
        <h2>Charge Point Simulator</h2>
        <p>Steuerung für OCPP-Demoaktionen</p>
      </header>

      <div className="simulator-panel__form">
        <label className="simulator-panel__field">
          <span>Charge Point ID</span>
          <input
            type="text"
            value={cpId}
            onChange={(event) => onCpIdChange(event.target.value)}
            placeholder="CP_1"
            autoComplete="off"
          />
        </label>

        <label className="simulator-panel__field">
          <span>RFID / idTag</span>
          <input
            type="text"
            value={idTag}
            onChange={(event) => setIdTag(event.target.value)}
            placeholder="RFID_DEMO"
            autoComplete="off"
          />
        </label>
      </div>

      <div className="simulator-panel__actions">
        <button type="button" onClick={handleConnect} disabled={isBusy}>
          Connect
        </button>
        <button type="button" onClick={handleDisconnect} disabled={isBusy}>
          Disconnect
        </button>
        <button type="button" onClick={handleSendRfid} disabled={isBusy}>
          RFID halten
        </button>
        <button type="button" onClick={handleStartTransaction} disabled={isBusy}>
          Start
        </button>
        <button type="button" onClick={handleStopTransaction} disabled={isBusy}>
          Stop
        </button>
        <button type="button" onClick={handleToggleHeartbeat} disabled={isBusy}>
          {heartbeatActive ? 'Heartbeats aus' : 'Heartbeats an'}
        </button>
      </div>

      <dl className="simulator-panel__state">
        <div>
          <dt>Heartbeat-Intervall</dt>
          <dd>{lastState ? `${lastState.interval}s` : '—'}</dd>
        </div>
        <div>
          <dt>Transaktion</dt>
          <dd>
            {lastState?.transactionId != null && lastState.transactionId >= 0
              ? `ID ${lastState.transactionId}`
              : 'keine aktive'}
          </dd>
        </div>
      </dl>

      {status && (
        <div className={`status-message status-message--${status.type}`} role="status">
          {status.text}
        </div>
      )}
    </section>
  )
}
