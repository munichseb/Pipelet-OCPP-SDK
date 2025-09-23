declare module 'rete-area-plugin' {
  import type { NodeEditor, Node } from 'rete'
  import type { Plugin } from 'rete/types/core/plugin'

  interface ZoomOptions {
    (editor: NodeEditor, nodes?: Node[]): void
  }

  interface AreaPluginOptions {
    background?: boolean | HTMLElement
    snap?: boolean | { size?: number }
    scaleExtent?: boolean | { min: number; max: number }
    translateExtent?: boolean | { width: number; height: number }
  }

  interface AreaPluginModule extends Plugin {
    install(editor: NodeEditor, options?: AreaPluginOptions): void
    zoomAt: ZoomOptions
  }

  const plugin: AreaPluginModule

  export default plugin
}
