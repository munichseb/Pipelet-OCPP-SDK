import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { createRoot } from 'react-dom/client'
import Rete, { Control, Input, Node as ReteNode, NodeEditor, Output, Socket } from 'rete'
import ConnectionPlugin from 'rete-connection-plugin'
import ReactRenderPlugin from 'rete-react-render-plugin'
import type { PipeletSummary, WorkflowGraph } from '../api'

type EditorJSON = ReturnType<NodeEditor['toJSON']>

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

    useEffect(() => {
      if (!containerRef.current) {
        return
      }

      const editor = new NodeEditor('pipelet-workflow@0.1.0', containerRef.current)
      editor.use(ConnectionPlugin)
      editor.use(ReactRenderPlugin, { createRoot })

      const pipeletComponent = new PipeletComponent()
      editor.register(pipeletComponent)

      const emitChange = (reason: 'load' | 'update') => {
        if (suppressEventsRef.current || !onChange) {
          return
        }
        const json = editor.toJSON() as unknown as WorkflowGraph
        onChange(json, reason)
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
      editor.trigger('process')

      return () => {
        editor.destroy()
        editorRef.current = null
        componentRef.current = null
      }
    }, [onChange])

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
              await editor.fromJSON(graph as unknown as EditorJSON)
            }
          } finally {
            suppressEventsRef.current = false
          }
          editor.view.resize()
          editor.trigger('process')
          onChange?.(editor.toJSON() as unknown as WorkflowGraph, 'load')
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
          onChange?.({}, 'load')
        },
      }),
      [onChange],
    )

    return <div ref={containerRef} className="workflow-canvas" />
  },
)

WorkflowCanvas.displayName = 'WorkflowCanvas'
