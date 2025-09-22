import { useEffect, useState } from 'react'
import { fetchPipelets, type PipeletSummary } from '../api'

interface PipeletPaletteProps {
  disabled?: boolean
  onAddPipelet: (pipelet: PipeletSummary) => Promise<void> | void
}

export function PipeletPalette({ disabled, onAddPipelet }: PipeletPaletteProps): JSX.Element {
  const [pipelets, setPipelets] = useState<PipeletSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    fetchPipelets()
      .then((data) => setPipelets(data))
      .catch((err) => {
        console.error('Pipelets konnten nicht geladen werden', err)
        setError('Pipelets konnten nicht geladen werden')
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <p className="palette-status">Pipelets werden geladen …</p>
  }

  if (error) {
    return (
      <div className="palette-status palette-status--error" role="alert">
        {error}
      </div>
    )
  }

  if (!pipelets.length) {
    return <p className="palette-status">Keine Pipelets vorhanden.</p>
  }

  return (
    <ul className="pipelet-list">
      {pipelets.map((pipelet) => (
        <li key={pipelet.id} className="pipelet-list__item">
          <div>
            <p className="pipelet-list__name">{pipelet.name}</p>
            <p className="pipelet-list__event">Event: {pipelet.event}</p>
          </div>
          <button type="button" onClick={() => onAddPipelet(pipelet)} disabled={disabled}>
            Hinzufügen
          </button>
        </li>
      ))}
    </ul>
  )
}
