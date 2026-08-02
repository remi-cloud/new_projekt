import { Link } from 'react-router-dom'

type Tool = {
  id: string
  name: string
  blurb: string
  to: string
  status: 'ready' | 'soon'
}

const TOOLS: Tool[] = [
  {
    id: 'singularity',
    name: 'Singularity',
    blurb:
      'Multi-agent LONG/SHORT: scoutowie globalni → specjaliści → orchestrator. Werdykt KUP/SPRZEDAJ na żądanie.',
    to: '/narzedzia/singularity',
    status: 'ready',
  },
]

export default function ToolsPage() {
  return (
    <div className="page tools-page">
      <div className="page-header">
        <div>
          <h1>Narzędzia</h1>
          <p className="page-lead">
            Moduły analityczne poza głównym przepływem pozycji. Włączasz gdy potrzebujesz — nie
            wiszą na banerze.
          </p>
        </div>
      </div>

      <div className="tools-grid">
        {TOOLS.map((tool) => (
          <Link
            key={tool.id}
            to={tool.to}
            className={`tool-card${tool.status === 'soon' ? ' soon' : ''}`}
          >
            <span className="tool-card-tag">Narzędzie</span>
            <strong>{tool.name}</strong>
            <p>{tool.blurb}</p>
            <span className="tool-card-cta">
              {tool.status === 'ready' ? 'Otwórz →' : 'Wkrótce'}
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}
