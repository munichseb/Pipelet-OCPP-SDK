declare module 'rete-react-render-plugin' {
  import type { ComponentType, ReactElement } from 'react'
  import type { Plugin } from 'rete'

  export interface ReactRenderPluginOptions {
    component?: ComponentType<any>
    createRoot?: (container: HTMLElement) => {
      render: (element: ReactElement) => void
      unmount: () => void
    }
  }

  export const Node: ComponentType<any>
  export const Socket: ComponentType<any>
  export const Control: ComponentType<any>

  const ReactRenderPlugin: Plugin & {
    name: string
    install: (editor: unknown, options?: ReactRenderPluginOptions) => void
  }

  export default ReactRenderPlugin
}
