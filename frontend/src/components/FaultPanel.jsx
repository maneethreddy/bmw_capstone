/**
 * FaultPanel — fault summary and recent fault windows.
 * All data from /api/faults and /api/summary — nothing invented.
 */
import { useMemo } from 'react'
import { round, formatTimestamp } from '../utils/formatters.js'

export default function FaultPanel({ faults, summary, loading }) {
  const totalFaults    = summary?.total_faults   ?? 0
  const faultVehicles  = useMemo(() => [...new Set(faults.map(r => r.vehicle_id))].sort(), [faults])
  const hasFaults      = totalFaults > 0

  return (
    <section aria-label="Fault monitoring" id="fault-panel">
      <div className="section-header">
        <div className="section-title">
          {hasFaults ? '🚨' : '✅'} Fault Monitoring
          {hasFaults && <span className="section-badge" style={{color:'var(--color-error)'}}>
            {totalFaults} total fault{totalFaults !== 1 ? 's' : ''}
          </span>}
        </div>
      </div>

      <div className={`fault-panel ${!hasFaults ? 'no-faults' : ''}`}>

        {/* Fault KPIs */}
        <div className="fault-summary-row">
          <div className="fault-stat">
            <span className="fault-stat-label">Total Faults</span>
            <span className={`fault-stat-value ${totalFaults === 0 ? 'zero' : ''}`}>
              {loading ? '…' : totalFaults}
            </span>
          </div>
          <div className="fault-stat">
            <span className="fault-stat-label">Affected Vehicles</span>
            <span className={`fault-stat-value ${faultVehicles.length === 0 ? 'zero' : ''}`}>
              {loading ? '…' : faultVehicles.length}
            </span>
          </div>
          <div className="fault-stat">
            <span className="fault-stat-label">Fault Windows</span>
            <span className={`fault-stat-value ${faults.length === 0 ? 'zero' : ''}`}>
              {loading ? '…' : faults.length}
            </span>
          </div>
        </div>

        {/* No-fault message */}
        {!loading && !hasFaults && (
          <div style={{ color: 'var(--color-success)', fontSize: 'var(--font-size-sm)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>✓</span>
            <span>No faults detected across all monitored windows.</span>
          </div>
        )}

        {/* Vehicles with faults */}
        {!loading && faultVehicles.length > 0 && (
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase', letterSpacing: '0.7px', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
              Vehicles with faults
            </div>
            <div className="fault-vehicle-list">
              {faultVehicles.map(v => (
                <span key={v} className="fault-vehicle-chip">{v}</span>
              ))}
            </div>
          </div>
        )}

        {/* Recent fault windows */}
        {!loading && faults.length > 0 && (
          <div>
            <div style={{ fontSize: 'var(--font-size-xs)', textTransform: 'uppercase', letterSpacing: '0.7px', color: 'var(--color-text-muted)', marginBottom: '8px' }}>
              Recent fault windows (most recent first)
            </div>
            <div className="table-wrapper" style={{ borderColor: 'rgba(239,68,68,0.2)' }}>
              <table className="telemetry-table">
                <thead>
                  <tr>
                    <th>Vehicle</th>
                    <th>Window Start</th>
                    <th>Fault Count</th>
                    <th>Max Temp</th>
                    <th>Avg Battery</th>
                    <th>Events</th>
                  </tr>
                </thead>
                <tbody>
                  {faults.slice(0, 10).map((row, i) => (
                    <tr key={`${row.vehicle_id}-${row.window_start}-${i}`} className="row-fault">
                      <td><span className="vehicle-id">{row.vehicle_id}</span></td>
                      <td>{formatTimestamp(row.window_start)}</td>
                      <td style={{ color: 'var(--color-error)', fontWeight: 700 }}>{row.fault_count}</td>
                      <td>{round(row.maximum_temperature, 1)} °C</td>
                      <td>{round(row.average_battery_level, 1)} %</td>
                      <td>{row.event_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
