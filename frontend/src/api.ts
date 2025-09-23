import axios, { AxiosHeaders } from 'axios'

const apiBaseURL = import.meta.env.VITE_API_BASE ?? ''

export const apiClient = axios.create({
  baseURL: apiBaseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

const TOKEN_STORAGE_KEY = 'pipelet.api.token'
export const API_TOKEN_CHANGED_EVENT = 'pipelet-token-change'
const isBrowser = typeof window !== 'undefined'

let authToken: string | null = null

function loadInitialToken(): string | null {
  if (!isBrowser) {
    return null
  }
  try {
    const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY)
    return stored && stored.trim() ? stored : null
  } catch (error) {
    console.warn('Konnte gespeichertes Token nicht laden', error)
    return null
  }
}

authToken = loadInitialToken()

if (authToken) {
  apiClient.defaults.headers.common.Authorization = `Bearer ${authToken}`
}

export function getApiToken(): string | null {
  return authToken
}

export function setApiToken(token: string | null): void {
  authToken = token && token.trim() ? token.trim() : null
  if (isBrowser) {
    try {
      if (authToken) {
        window.localStorage.setItem(TOKEN_STORAGE_KEY, authToken)
      } else {
        window.localStorage.removeItem(TOKEN_STORAGE_KEY)
      }
    } catch (error) {
      console.warn('Konnte Token nicht im Speicher aktualisieren', error)
    }
    window.dispatchEvent(new CustomEvent(API_TOKEN_CHANGED_EVENT))
  }
  if (authToken) {
    apiClient.defaults.headers.common.Authorization = `Bearer ${authToken}`
  } else {
    delete apiClient.defaults.headers.common.Authorization
  }
}

apiClient.interceptors.request.use((config) => {
  if (authToken) {
    if (config.headers) {
      if (typeof config.headers.set === 'function') {
        config.headers.set('Authorization', `Bearer ${authToken}`)
      } else {
        ;(config.headers as Record<string, string>).Authorization = `Bearer ${authToken}`
      }
    } else {
      config.headers = new AxiosHeaders({ Authorization: `Bearer ${authToken}` })
    }
  }
  return config
})

export interface PipeletSummary {
  id: number
  name: string
  event: string
}

export interface WorkflowSummary {
  id: number
  name: string
}

export interface WorkflowDetail extends WorkflowSummary {
  graph_json: WorkflowGraph
}

export interface WorkflowCreatePayload {
  name: string
}

export interface WorkflowUpdatePayload {
  name?: string
  graph_json: WorkflowGraph
}

export type WorkflowGraph = Record<string, unknown>

export type LogSource = 'cp' | 'cs' | 'pipelet'

export interface LogEntry {
  id: number
  source: LogSource
  message: string
  createdAt: string
}

export interface SimulatorState {
  interval: number
  transactionId: number | null
}

export interface SimulatorStatus {
  connected: boolean
  lastEventTs: string | null
}

export type ApiTokenRole = 'admin' | 'readonly'

export interface ApiTokenInfo {
  id: number
  name: string
  role: ApiTokenRole
  created_at: string
  revoked_at: string | null
}

export interface ApiTokenCreateResponse extends ApiTokenInfo {
  token: string
}

export async function fetchPipelets(): Promise<PipeletSummary[]> {
  const response = await apiClient.get('/api/pipelets')
  return (response.data as Array<Record<string, unknown>>).map((pipelet) => ({
    id: Number(pipelet.id),
    name: String(pipelet.name ?? ''),
    event: String(pipelet.event ?? ''),
  }))
}

export async function listWorkflows(): Promise<WorkflowSummary[]> {
  const response = await apiClient.get('/api/workflows')
  return (response.data as Array<Record<string, unknown>>).map((workflow) => ({
    id: Number(workflow.id),
    name: String(workflow.name ?? ''),
  }))
}

export async function createWorkflow(payload: WorkflowCreatePayload): Promise<WorkflowDetail> {
  const response = await apiClient.post('/api/workflows', payload)
  return normalizeWorkflow(response.data)
}

export async function getWorkflow(workflowId: number): Promise<WorkflowDetail> {
  const response = await apiClient.get(`/api/workflows/${workflowId}`)
  return normalizeWorkflow(response.data)
}

export async function updateWorkflow(
  workflowId: number,
  payload: WorkflowUpdatePayload,
): Promise<WorkflowDetail> {
  const response = await apiClient.put(`/api/workflows/${workflowId}`, payload)
  return normalizeWorkflow(response.data)
}

function normalizeWorkflow(data: Record<string, unknown>): WorkflowDetail {
  let graph: WorkflowGraph = {}
  const rawGraph = data.graph_json
  if (typeof rawGraph === 'string' && rawGraph.trim()) {
    try {
      graph = JSON.parse(rawGraph) as WorkflowGraph
    } catch (error) {
      console.warn('Konnte graph_json nicht parsen, verwende Rohwert', error)
      graph = {} as WorkflowGraph
    }
  } else if (rawGraph && typeof rawGraph === 'object') {
    graph = rawGraph as WorkflowGraph
  }
  return {
    id: Number(data.id),
    name: String(data.name ?? ''),
    graph_json: graph,
  }
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data
    if (responseData && typeof responseData === 'object' && 'error' in responseData) {
      const message = (responseData as Record<string, unknown>).error
      if (typeof message === 'string' && message.trim()) {
        return message
      }
    }
    if (typeof error.message === 'string' && error.message.trim()) {
      return error.message
    }
  } else if (error instanceof Error) {
    return error.message
  }
  return 'Unbekannter Fehler'
}

export async function fetchLogs(params: { source?: LogSource; limit?: number }): Promise<LogEntry[]> {
  const { source, limit = 200 } = params
  const response = await apiClient.get('/api/logs', {
    params: {
      source,
      limit,
    },
  })
  return Array.isArray(response.data)
    ? (response.data as Array<Record<string, unknown>>).map(normalizeLogEntry)
    : []
}

export async function downloadLogs(
  source: LogSource | 'all',
  limit = 200,
): Promise<Blob> {
  const params: Record<string, string | number | undefined> = {
    limit,
  }
  if (source !== 'all') {
    params.source = source
  }
  const response = await apiClient.get('/api/logs/download', {
    params,
    responseType: 'blob',
  })
  return response.data as Blob
}

export async function getSimulatorStatus(cpId: string): Promise<SimulatorStatus> {
  const response = await apiClient.get('/api/sim/status', {
    params: {
      cp_id: cpId,
    },
  })
  return normalizeSimulatorStatus(response.data)
}

export async function connectSimulator(cpId: string): Promise<SimulatorState> {
  const response = await apiClient.post('/api/sim/connect', {
    cp_id: cpId,
  })
  return normalizeSimulatorState(response.data)
}

export async function disconnectSimulator(cpId: string): Promise<SimulatorState> {
  const response = await apiClient.post('/api/sim/disconnect', {
    cp_id: cpId,
  })
  return normalizeSimulatorState(response.data)
}

export async function startSimulatorHeartbeat(cpId: string): Promise<SimulatorState> {
  const response = await apiClient.post('/api/sim/heartbeat/start', {
    cp_id: cpId,
  })
  return normalizeSimulatorState(response.data)
}

export async function stopSimulatorHeartbeat(cpId: string): Promise<SimulatorState> {
  const response = await apiClient.post('/api/sim/heartbeat/stop', {
    cp_id: cpId,
  })
  return normalizeSimulatorState(response.data)
}

export async function sendSimulatorRfid(cpId: string, idTag: string): Promise<SimulatorState> {
  const response = await apiClient.post('/api/sim/rfid', {
    cp_id: cpId,
    idTag,
  })
  return normalizeSimulatorState(response.data)
}

export async function startSimulatorTransaction(
  cpId: string,
  idTag: string,
): Promise<SimulatorState> {
  const response = await apiClient.post('/api/sim/start', {
    cp_id: cpId,
    idTag,
  })
  return normalizeSimulatorState(response.data)
}

export async function stopSimulatorTransaction(cpId: string): Promise<SimulatorState> {
  const response = await apiClient.post('/api/sim/stop', {
    cp_id: cpId,
  })
  return normalizeSimulatorState(response.data)
}

export async function getHealthStatus(): Promise<boolean> {
  try {
    const response = await apiClient.get('/api/health')
    return response.status === 200
  } catch {
    return false
  }
}

export async function listApiTokens(): Promise<ApiTokenInfo[]> {
  const response = await apiClient.get('/api/auth/tokens')
  return Array.isArray(response.data)
    ? (response.data as Array<Record<string, unknown>>).map((item) => ({
        id: Number(item.id),
        name: String(item.name ?? ''),
        role: (item.role as ApiTokenRole) ?? 'readonly',
        created_at: String(item.created_at ?? ''),
        revoked_at:
          typeof item.revoked_at === 'string' && item.revoked_at.trim()
            ? String(item.revoked_at)
            : null,
      }))
    : []
}

export async function createApiToken(payload: {
  name: string
  role: ApiTokenRole
}): Promise<ApiTokenCreateResponse> {
  const response = await apiClient.post('/api/auth/tokens', payload)
  const data = response.data as Record<string, unknown>
  return {
    id: Number(data.id),
    name: String(data.name ?? payload.name),
    role: (data.role as ApiTokenRole) ?? payload.role,
    created_at: String(data.created_at ?? ''),
    revoked_at:
      typeof data.revoked_at === 'string' && data.revoked_at.trim()
        ? String(data.revoked_at)
        : null,
    token: String(data.token ?? ''),
  }
}

export async function revokeApiToken(tokenId: number): Promise<void> {
  await apiClient.delete(`/api/auth/tokens/${tokenId}`)
}

function normalizeLogEntry(data: Record<string, unknown>): LogEntry {
  return {
    id: Number(data.id ?? 0),
    source: (data.source as LogSource) ?? 'pipelet',
    message: String(data.message ?? ''),
    createdAt: String(data.createdAt ?? ''),
  }
}

function normalizeSimulatorState(data: Record<string, unknown>): SimulatorState {
  const transactionId = data.transactionId
  return {
    interval: Number(data.interval ?? 0),
    transactionId:
      typeof transactionId === 'number'
        ? transactionId
        : transactionId == null
          ? null
          : Number(transactionId),
  }
}

function normalizeSimulatorStatus(data: Record<string, unknown>): SimulatorStatus {
  const lastEvent = data.last_event_ts
  return {
    connected: Boolean(data.connected),
    lastEventTs:
      typeof lastEvent === 'string' && lastEvent.trim() ? lastEvent : null,
  }
}
