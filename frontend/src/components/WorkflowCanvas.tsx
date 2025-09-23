import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { createRoot } from 'react-dom/client'
import Rete, { Control, Input, Node as ReteNode, NodeEditor, Output, Socket } from 'rete'
import AreaPlugin from 'rete-area-plugin'
import ConnectionPlugin from 'rete-connection-plugin'
import ReactRenderPlugin from 'rete-react-render-plugin'
import type { Plugin } from 'rete/types/core/plugin'
import type { PipeletSummary, WorkflowGraph } from '../api'

type EditorJSON = ReturnType<NodeEditor['toJSON']>

type Mutable<T> = { -readonly [P in keyof T]: T[P] }

function cloneGraph(graph: WorkflowGraph): EditorJSON {
  return JSON.parse(JSON.stringify(graph)) as EditorJSON
}

function normalizeLegacyNode(node: Mutable<Record<string, unknown>>): void {
  const data = (node.data ?? {}) as Mutable<Record<string, unknown>>
  const pipelet = (data.pipelet ?? {}) as Record<string, unknown>

  if (data.pipeletId == null) {
    const rawId = data.pipelet_id ?? pipelet.id
    if (typeof rawId === 'number') {
      data.pipeletId = rawId
    }
  }

  if (typeof data.name !== 'string' || data.name.trim() === '') {
    const name = (typeof data.name === 'string' && data.name.trim() !== ''
      ? data.name
      : pipelet.name) as string | undefined
    if (name) {
      data.name = name
    }
  }

  if (typeof data.event !== 'string' || data.event.trim() === '') {
    const event = (typeof data.event === 'string' && data.event.trim() !== ''
      ? data.event
      : pipelet.event) as string | undefined
    if (event) {
      data.event = event
    }
  }

  node.data = data

  const outputs = (node.outputs ?? {}) as Mutable<Record<string, unknown>>
  if ('out' in outputs && !('output' in outputs)) {
    const legacyOutput = outputs.out as Mutable<Record<string, unknown>>
    const connections = Array.isArray(legacyOutput.connections)
      ? (legacyOutput.connections as Array<Mutable<Record<string, unknown>>>)
      : []
    connections.forEach((connection) => {
      if (!('output' in connection)) {
        connection.output = 'output'
      }
      if (!('input' in connection)) {
        connection.input = 'input'
      }
    })

    outputs.output = {
      ...legacyOutput,
      connections,
    }
    delete outputs.out
  }
  node.outputs = outputs

  const inputs = (node.inputs ?? {}) as Mutable<Record<string, unknown>>
  if ('in' in inputs && !('input' in inputs)) {
    inputs.input = inputs.in
    delete inputs.in
  }
  node.inputs = inputs
}

function normalizeGraph(graph: WorkflowGraph): EditorJSON {
  const cloned = cloneGraph(graph)
  const nodes = (cloned.nodes ?? {}) as Record<string, unknown>
  Object.values(nodes).forEach((rawNode) => {
    if (rawNode && typeof rawNode === 'object') {
      normalizeLegacyNode(rawNode as Mutable<Record<string, unknown>>)
    }
  })
  return cloned
}

interface WorkflowCanvasProps {
  onChange?: (graph: WorkflowGraph, reason: 'load' | 'update') => void
}

export interface WorkflowCanvasHandle {
  addPipelet(pipelet: PipeletSummary): Promise<void>
  getGraph(): Promise<WorkflowGraph | null>
  loadGraph(graph: WorkflowGraph | null | undefined): Promise<void>
  reset(): Promise<void>
}

interface PipeletNodeData {
  pipeletId: number
  name: string
  event: string
}

class PipeletInfoControl extends Control {
  constructor(event: string) {
    super('pipelet-info')
    const control = this as unknown as Control & {
      render: string
      component: (props: { event?: string }) => JSX.Element
      props: { event: string }
    }
    control.render = 'react'
    control.component = ({ event: eventName }) => (
      <div className="pipelet-node__event">{eventName || 'Kein Event'}</div>
    )
    control.props = { event }
  }
}

const pipeletSocket = new Socket('Pipelet')

class PipeletComponent extends Rete.Component {
  constructor() {
    super('Pipelet')
  }

  async builder(node: ReteNode): Promise<void> {
    const data = node.data as unknown as PipeletNodeData
    node.name = data.name || 'Pipelet'
    node.meta = node.meta || {}
    node.meta.pipeletId = data.pipeletId
    node.addInput(new Input('input', 'Input', pipeletSocket, true))
    node.addOutput(new Output('output', 'Output', pipeletSocket))
    node.addControl(new PipeletInfoControl(data.event))
  }

  worker(): void {}
}

export const WorkflowCanvas = forwardRef<WorkflowCanvasHandle, WorkflowCanvasProps>(
  ({ onChange }, ref) => {
    const containerRef = useRef<HTMLDivElement | null>(null)
    const editorRef = useRef<NodeEditor | null>(null)
    const componentRef = useRef<PipeletComponent | null>(null)
    const suppressEventsRef = useRef(false)
    const onChangeRef = useRef(onChange)

    useEffect(() => {
      onChangeRef.current = onChange
    }, [onChange])

    useEffect(() => {
      if (!containerRef.current) {
        return
      }

      const editor = new NodeEditor('pipelet-workflow@0.1.0', containerRef.current)
      editor.use(ConnectionPlugin)
      editor.use(
        // rete-area-plugin does not ship TypeScript definitions.
        AreaPlugin as unknown as Plugin,
        { background: true } as unknown as void,
      )
      editor.use(ReactRenderPlugin, { createRoot })

      const pipeletComponent = new PipeletComponent()
      editor.register(pipeletComponent)

      const emitChange = (reason: 'load' | 'update') => {
        const callback = onChangeRef.current
        if (suppressEventsRef.current || !callback) {
          return
        }
        const json = editor.toJSON() as unknown as WorkflowGraph
        callback(json, reason)
      }

      const handleUpdate = () => emitChange('update')
      const events = [
        'nodecreated',
        'noderemoved',
        'connectioncreated',
        'connectionremoved',
        'nodetranslated',
      ] as const
      events.forEach((event) => editor.on(event, handleUpdate))

      editorRef.current = editor
      componentRef.current = pipeletComponent

      editor.view.resize()
      AreaPlugin.zoomAt(editor)
      editor.trigger('process')

      return () => {
        editor.destroy()
        editorRef.current = null
        componentRef.current = null
      }
    }, [])

    useImperativeHandle(
      ref,
      () => ({
        async addPipelet(pipelet) {
          const editor = editorRef.current
          const component = componentRef.current
          if (!editor || !component) {
            return
          }
          const node = await component.createNode({
            pipeletId: pipelet.id,
            name: pipelet.name,
            event: pipelet.event,
          })
          const offset = editor.nodes.length * 180
          node.position = [60 + offset, 60 + (offset % 240)]
          editor.addNode(node)
          editor.trigger('process')
        },
        async getGraph() {
          const editor = editorRef.current
          return editor ? (editor.toJSON() as unknown as WorkflowGraph) : null
        },
        async loadGraph(graph) {
          const editor = editorRef.current
          if (!editor) {
            return
          }
          suppressEventsRef.current = true
          try {
            editor.clear()
            if (graph && Object.keys(graph).length > 0) {
              await editor.fromJSON(normalizeGraph(graph))
            }
          } finally {
            suppressEventsRef.current = false
          }
          editor.view.resize()
          AreaPlugin.zoomAt(editor)
          editor.trigger('process')
          const callback = onChangeRef.current
          callback?.(editor.toJSON() as unknown as WorkflowGraph, 'load')
        },
        async reset() {
          const editor = editorRef.current
          if (!editor) {
            return
          }
          suppressEventsRef.current = true
          editor.clear()
          suppressEventsRef.current = false
          editor.trigger('process')
          AreaPlugin.zoomAt(editor)
          const callback = onChangeRef.current
          callback?.({}, 'load')
        },
      }),
      [],
    )

    return <div ref={containerRef} className="workflow-canvas" />
  },
)

WorkflowCanvas.displayName = 'WorkflowCanvas'
