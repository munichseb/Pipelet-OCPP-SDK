declare module 'rete-react-render-plugin' {
  import type { ComponentType, ReactElement } from 'react'
  import type { Plugin } from 'rete'

  export interface ReactRenderPluginOptions {
    component?: ComponentType<Record<string, unknown>>
    createRoot?: (container: HTMLElement) => {
      render: (element: ReactElement) => void
      unmount: () => void
    }
  }

  export const Node: ComponentType<Record<string, unknown>>
  export const Socket: ComponentType<Record<string, unknown>>
  export const Control: ComponentType<Record<string, unknown>>

  const ReactRenderPlugin: Plugin & {
    name: string
    install: (editor: unknown, options?: ReactRenderPluginOptions) => void
  }

  export default ReactRenderPlugin
}
