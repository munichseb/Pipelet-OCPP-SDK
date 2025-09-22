import axios from 'axios'

const apiBaseURL = import.meta.env.VITE_API_BASE ?? ''

export const apiClient = axios.create({
  baseURL: apiBaseURL,
  headers: {
    'Content-Type': 'application/json',
  },
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
