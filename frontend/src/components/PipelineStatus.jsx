/**
 * PipelineStatus — visual Kafka → Spark → S3 → Athena stage strip.
 * Premium animated design with glowing connectors.
 */

const STAGES = [
  { id: 'kafka',  icon: '📨', name: 'Kafka',  desc: 'Message Broker',     color: '#e879f9' },
  { id: 'spark',  icon: '⚡', name: 'Spark',  desc: 'Stream Processing',   color: '#f59e0b' },
  { id: 's3',     icon: '🪣', name: 'S3',     desc: 'Object Storage',      color: '#38bdf8' },
  { id: 'athena', icon: '🔍', name: 'Athena', desc: 'Analytical Query',    color: '#10d97e' },
]

export default function PipelineStatus({ apiStatus }) {
  const active = apiStatus === 'online'

  return (
    <section aria-label="Pipeline stage status">
      <div className="section-header">
        <div className="section-title">🔁 Data Pipeline</div>
        {active && (
          <span className="section-badge" style={{ color: 'var(--color-success)', borderColor: 'rgba(16,217,126,0.3)', background: 'rgba(16,217,126,0.08)' }}>
            ● Streaming
          </span>
        )}
      </div>
      <nav className="pipeline-track" aria-label="Pipeline stages">
        {STAGES.map((stage, i) => (
          <div key={stage.id} style={{ display: 'flex', alignItems: 'center' }}>
            <div
              className="pipeline-stage"
              id={`pipeline-stage-${stage.id}`}
              title={stage.desc}
            >
              {active && (
                <span
                  className="pipeline-stage-dot"
                  aria-label={`${stage.name} active`}
                  style={{ background: stage.color, boxShadow: `0 0 8px ${stage.color}` }}
                />
              )}
              <span className="pipeline-stage-icon" aria-hidden="true">{stage.icon}</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                <span className="pipeline-stage-name">{stage.name}</span>
                <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', fontWeight: 400 }}>
                  {stage.desc}
                </span>
              </div>
            </div>
            {i < STAGES.length - 1 && (
              <div style={{ display: 'flex', alignItems: 'center', padding: '0 4px' }}>
                <svg width="32" height="16" viewBox="0 0 32 16" fill="none" style={{ flexShrink: 0 }}>
                  <line
                    x1="0" y1="8" x2="24" y2="8"
                    stroke={active ? 'rgba(61,134,232,0.6)' : 'rgba(90,110,138,0.3)'}
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                  />
                  <polygon
                    points="22,4 32,8 22,12"
                    fill={active ? 'rgba(61,134,232,0.7)' : 'rgba(90,110,138,0.3)'}
                  />
                </svg>
              </div>
            )}
          </div>
        ))}

      </nav>
    </section>
  )
}
