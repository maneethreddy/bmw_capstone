/**
 * SummaryCards — fleet-level KPI cards.
 * All values sourced from /api/summary — nothing is invented.
 */
import { round } from '../utils/formatters.js'

const CARDS = [
  {
    id:    'vehicles',
    icon:  '🚗',
    label: 'Vehicles Monitored',
    key:   'total_vehicles',
    unit:  '',
    decimals: 0,
    cls:   '',
  },
  {
    id:    'events',
    icon:  '📡',
    label: 'Events Processed',
    key:   'total_events',
    unit:  '',
    decimals: 0,
    cls:   '',
  },
  {
    id:    'windows',
    icon:  '🪟',
    label: 'Aggregate Windows',
    key:   'total_windows',
    unit:  '',
    decimals: 0,
    cls:   '',
  },
  {
    id:    'faults',
    icon:  '⚠️',
    label: 'Faults Detected',
    key:   'total_faults',
    unit:  '',
    decimals: 0,
    cls:   'fault',
  },
  {
    id:    'speed',
    icon:  '⚡',
    label: 'Avg Speed',
    key:   'avg_speed',
    unit:  'km/h',
    decimals: 1,
    cls:   '',
  },
  {
    id:    'battery',
    icon:  '🔋',
    label: 'Avg Battery',
    key:   'avg_battery',
    unit:  '%',
    decimals: 1,
    cls:   '',
  },
  {
    id:    'temp',
    icon:  '🌡️',
    label: 'Max Temperature',
    key:   'max_temperature',
    unit:  '°C',
    decimals: 1,
    cls:   '',
  },
]

export default function SummaryCards({ summary, loading }) {
  return (
    <section aria-label="Fleet summary KPIs">
      <div className="summary-grid">
        {CARDS.map(card => (
          <article
            key={card.id}
            id={`kpi-${card.id}`}
            className={`kpi-card ${card.cls}`}
            aria-label={card.label}
          >
            <div className="kpi-icon" aria-hidden="true">{card.icon}</div>
            <div className="kpi-label">{card.label}</div>
            {loading || !summary ? (
              <div className="skeleton" style={{ width: '60%', height: '2rem', marginTop: '4px' }} />
            ) : (
              <div className="kpi-value">
                {round(summary[card.key], card.decimals)}
                {card.unit && <span className="kpi-unit">{card.unit}</span>}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
