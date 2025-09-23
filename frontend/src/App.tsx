import { isAxiosError } from 'axios'
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from 'react'
import {
  createWorkflow,
  getWorkflow,
  listWorkflows,
  updateWorkflow,
  type PipeletSummary,
  type WorkflowDetail,
  type WorkflowGraph,
  type WorkflowSummary,
  getErrorMessage,
  importConfiguration,
} from './api'
import { PipeletPalette } from './components/PipeletPalette'
import { LogViewer } from './components/LogViewer'
import { SimulatorPanel } from './components/SimulatorPanel'
import { StatusBars } from './components/StatusBars'
import {
  WorkflowCanvas,
  type WorkflowCanvasHandle,
} from './components/WorkflowCanvas'
import { TokenPanel } from './components/TokenPanel'
import { createSeedPayload } from './seed'

interface StatusMessage {
  type: 'success' | 'error'
  text: string
}

function App(): JSX.Element {
  const canvasRef = useRef<WorkflowCanvasHandle>(null)
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([])
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<number | ''>('')
  const [activeWorkflow, setActiveWorkflow] = useState<WorkflowDetail | null>(null)
  const [graph, setGraph] = useState<WorkflowGraph | null>(null)
  const [isDirty, setIsDirty] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [status, setStatus] = useState<StatusMessage | null>(null)
  const [cpId, setCpId] = useState('CP_1')
  const [statusRevision, setStatusRevision] = useState(0)

  useEffect(() => {
    listWorkflows()
      .then((data) =>
        setWorkflows([...data].sort((a, b) => a.name.localeCompare(b.name))),
      )
      .catch((error) => reportError('Workflows konnten nicht geladen werden', error))
  }, [])

  useEffect(() => {
    if (status === null) {
      return
    }
    const timeout = window.setTimeout(() => setStatus(null), 4000)
    return () => window.clearTimeout(timeout)
  }, [status])

  const workflowName = activeWorkflow?.name ?? 'Unbenannt'

  const reportError = (message: string, error: unknown): void => {
    console.error(message, error)

    let detail: string | null = null
    if (isAxiosError(error) && error.response?.status === 401) {
      detail = 'Zugriff verweigert. Bitte gültiges API-Token im Bereich „API Tokens“ speichern.'
    } else {
      const extracted = getErrorMessage(error)
      if (extracted && extracted !== 'Unbekannter Fehler') {
        detail = extracted
      }
    }

    setStatus({
      type: 'error',
      text: detail ? `${message}: ${detail}` : message,
    })
  }

  const handleSimulatorActionComplete = (): void => {
    setStatusRevision((previous) => previous + 1)
  }

  const handleAddPipelet = async (pipelet: PipeletSummary): Promise<void> => {
    try {
      await canvasRef.current?.addPipelet(pipelet)
    } catch (error) {
      reportError('Pipelet konnte nicht platziert werden', error)
    }
  }

  const handleWorkflowLoad = async (workflowId: number): Promise<void> => {
    setIsLoading(true)
    try {
      const detail = await getWorkflow(workflowId)
      setActiveWorkflow(detail)
      setGraph(detail.graph_json)
      setSelectedWorkflowId(workflowId)
      await canvasRef.current?.loadGraph(detail.graph_json)
      setIsDirty(false)
      setStatus({ type: 'success', text: `Workflow "${detail.name}" geladen` })
    } catch (error) {
      reportError('Workflow konnte nicht geladen werden', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectChange = (event: ChangeEvent<HTMLSelectElement>): void => {
    const value = event.target.value
    setSelectedWorkflowId(value ? Number(value) : '')
  }

  const handleCreateWorkflow = async (): Promise<void> => {
    const name = window.prompt('Name für neuen Workflow eingeben')?.trim()
    if (!name) {
      return
    }
    setIsLoading(true)
    try {
      const created = await createWorkflow({ name })
      setWorkflows((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)))
      setActiveWorkflow(created)
      setGraph(created.graph_json)
      setSelectedWorkflowId(created.id)
      await canvasRef.current?.reset()
      setIsDirty(false)
      setStatus({ type: 'success', text: `Workflow "${created.name}" erstellt` })
    } catch (error) {
      reportError('Workflow konnte nicht erstellt werden', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveWorkflow = async (): Promise<void> => {
    if (!activeWorkflow) {
      reportError('Kein Workflow ausgewählt', null)
      return
    }
    setIsLoading(true)
    try {
      const latestGraph = (await canvasRef.current?.getGraph()) ?? graph ?? {}
      const updated = await updateWorkflow(activeWorkflow.id, {
        name: activeWorkflow.name,
        graph_json: latestGraph,
      })
      setActiveWorkflow(updated)
      setGraph(updated.graph_json)
      setIsDirty(false)
      setWorkflows((prev) => {
        const next = prev.map((workflow) =>
          workflow.id === updated.id ? updated : workflow,
        )
        return next.sort((a, b) => a.name.localeCompare(b.name))
      })
      setStatus({ type: 'success', text: 'Workflow gespeichert' })
    } catch (error) {
      reportError('Workflow konnte nicht gespeichert werden', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleImportSeed = async (): Promise<void> => {
    const confirmed = window.confirm(
      'Seed-Daten importieren? Bestehende Pipelets und Workflows werden überschrieben.',
    )
    if (!confirmed) {
      return
    }

    setIsLoading(true)
    try {
      const payload = createSeedPayload()
      const result = await importConfiguration(payload, { overwrite: true })
      const workflowList = await listWorkflows()
      setWorkflows([...workflowList].sort((a, b) => a.name.localeCompare(b.name)))

      if (activeWorkflow) {
        try {
          const detail = await getWorkflow(activeWorkflow.id)
          setActiveWorkflow(detail)
          setGraph(detail.graph_json)
          await canvasRef.current?.loadGraph(detail.graph_json)
          setIsDirty(false)
        } catch (error) {
          console.error('Konnte aktiven Workflow nach Seed-Import nicht aktualisieren', error)
        }
      }

      setStatus({
        type: 'success',
        text: `Seed importiert (erstellt: ${result.created}, aktualisiert: ${result.updated})`,
      })
    } catch (error) {
      reportError('Seed konnte nicht importiert werden', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCanvasChange = (updated: WorkflowGraph, reason: 'load' | 'update'): void => {
    setGraph(updated)
    setIsDirty(reason === 'update')
  }

  const workflowOptions = useMemo(() => {
    if (!workflows.length) {
      return [
        <option key="placeholder" value="">
          Keine Workflows vorhanden
        </option>,
      ]
    }
    return [
      <option key="placeholder" value="">
        Workflow auswählen
      </option>,
      ...workflows.map((workflow) => (
        <option key={workflow.id} value={workflow.id}>
          {workflow.name}
        </option>
      )),
    ]
  }, [workflows])

  return (
    <div className="app-layout">
      <header className="app-header">
        <div>
          <h1>Pipelet Workflow Canvas</h1>
          <p className="app-subtitle">Aktueller Workflow: {workflowName}</p>
        </div>
        <div className="workflow-controls">
          <label className="visually-hidden" htmlFor="workflow-select">
            Workflow auswählen
          </label>
          <select
            id="workflow-select"
            className="workflow-select"
            value={selectedWorkflowId}
            onChange={handleSelectChange}
            disabled={isLoading}
          >
            {workflowOptions}
          </select>
          <button type="button" onClick={() => selectedWorkflowId && handleWorkflowLoad(Number(selectedWorkflowId))} disabled={isLoading || !selectedWorkflowId}>
            Laden
          </button>
          <button type="button" onClick={handleCreateWorkflow} disabled={isLoading}>
            Neu
          </button>
          <button
            type="button"
            onClick={handleSaveWorkflow}
            disabled={isLoading || !activeWorkflow || !graph || !isDirty}
          >
            Speichern
          </button>
          <button type="button" onClick={handleImportSeed} disabled={isLoading}>
            Seed importieren
          </button>
        </div>
        {status && (
          <div className={`status-message status-message--${status.type}`} role={status.type === 'error' ? 'alert' : 'status'}>
            {status.text}
          </div>
        )}
      </header>
      <StatusBars cpId={cpId} refreshToken={statusRevision} />
      <main className="app-main">
        <aside className="palette-column">
          <TokenPanel />
          <h2 className="section-title">Pipelets</h2>
          <PipeletPalette onAddPipelet={handleAddPipelet} disabled={!activeWorkflow} />
        </aside>
        <section className="canvas-column">
          <WorkflowCanvas ref={canvasRef} onChange={handleCanvasChange} />
        </section>
      </main>
      <section className="app-panels">
        <aside className="app-panels__simulator">
          <SimulatorPanel
            cpId={cpId}
            onCpIdChange={setCpId}
            onActionComplete={handleSimulatorActionComplete}
          />
        </aside>
        <div className="app-panels__logs">
          <LogViewer />
        </div>
      </section>
    </div>
  )
}

export default App
