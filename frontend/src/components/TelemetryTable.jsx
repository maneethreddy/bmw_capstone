/**
 * TelemetryTable — sortable table of aggregated windows.
 * Status column is derived from actual fault_count and sensor readings.
 */
import { useState, useMemo, useRef, useEffect } from 'react'
import { round, formatTimestamp, deriveStatus } from '../utils/formatters.js'

const COLUMNS = [
  { key: 'batch_id',             label: 'Batch',          sortable: true  },
  { key: 'vehicle_id',           label: 'Vehicle ID',     sortable: true  },
  { key: 'window_start',         label: 'Window Start',   sortable: true  },
  { key: 'window_end',           label: 'Window End',     sortable: false },
  { key: 'average_speed',        label: 'Avg Speed',      sortable: true, unit: 'km/h', decimals: 1 },
  { key: 'average_battery_level',label: 'Avg Battery',    sortable: true, unit: '%',    decimals: 1 },
  { key: 'maximum_temperature',  label: 'Max Temp',       sortable: true, unit: '°C',   decimals: 1 },
  { key: 'fault_count',          label: 'Faults',         sortable: true  },
  { key: 'event_count',          label: 'Events',         sortable: true  },
  { key: '_status',              label: 'Status',         sortable: false },
]

function sortRows(rows, key, dir) {
  if (!key) return rows
  return [...rows].sort((a, b) => {
    let av = a[key]; let bv = b[key]
    if (key === 'window_start' || key === 'vehicle_id') { av = av || ''; bv = bv || '' }
    else { av = av !== undefined && av !== null ? parseFloat(av) : -1; bv = bv !== undefined && bv !== null ? parseFloat(bv) : -1 }
    if (av < bv) return dir === 'asc' ? -1 : 1
    if (av > bv) return dir === 'asc' ?  1 : -1
    return 0
  })
}

export default function TelemetryTable({ telemetry, loading, newData }) {
  const [sortKey, setSortKey] = useState('window_start')
  const [sortDir, setSortDir] = useState('desc')
  const [selectedBatch, setSelectedBatch] = useState('all')
  const [recentlyAddedKeys, setRecentlyAddedKeys] = useState(new Set())
  const prevRowsRef = useRef(new Map())
  const isInitialMount = useRef(true)

  useEffect(() => {
    if (loading || !telemetry || telemetry.length === 0) return

    if (isInitialMount.current) {
      isInitialMount.current = false
      const initialMap = new Map()
      telemetry.forEach(row => {
        initialMap.set(`${row.vehicle_id}-${row.window_start}`, row.event_count)
      })
      prevRowsRef.current = initialMap
      return
    }

    const newKeys = new Set()
    const currentMap = new Map()

    telemetry.forEach(row => {
      const key = `${row.vehicle_id}-${row.window_start}`
      currentMap.set(key, row.event_count)
      const prevEvents = prevRowsRef.current.get(key)
      if (prevEvents === undefined || row.event_count > prevEvents) {
        newKeys.add(key)
      }
    })

    prevRowsRef.current = currentMap

    if (newKeys.size > 0) {
      setRecentlyAddedKeys(newKeys)
      const timer = setTimeout(() => {
        setRecentlyAddedKeys(new Set())
      }, 3500)
      return () => clearTimeout(timer)
    }
  }, [telemetry, loading])

  // Collect distinct batch IDs present in data, sorted descending
  const availableBatches = useMemo(() => {
    const set = new Set()
    telemetry.forEach(r => {
      if (r.batch_id !== undefined && r.batch_id !== null) {
        set.add(r.batch_id)
      }
    })
    return Array.from(set).sort((a, b) => b - a)
  }, [telemetry])

  // Filter by selected batch
  const filteredRows = useMemo(() => {
    if (selectedBatch === 'all') return telemetry
    return telemetry.filter(r => r.batch_id === selectedBatch)
  }, [telemetry, selectedBatch])

  function handleSort(key) {
    if (!key) return
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const sorted = useMemo(() => sortRows(filteredRows, sortKey, sortDir), [filteredRows, sortKey, sortDir])

  const arrowIcon = (col) => {
    if (!col.sortable) return null
    if (sortKey !== col.key) return <span className="sort-icon">↕</span>
    return <span className="sort-icon">{sortDir === 'asc' ? '↑' : '↓'}</span>
  }

  if (loading) {
    return (
      <div className="card">
        <div className="state-center">
          <div className="state-icon">⟳</div>
          <span>Loading telemetry windows…</span>
        </div>
      </div>
    )
  }

  if (!loading && telemetry.length === 0) {
    return (
      <div className="card">
        <div className="state-center">
          <div className="state-icon">📭</div>
          <span>No telemetry windows yet.</span>
          <small>Start the PySpark pipeline and generate events to see data here.</small>
        </div>
      </div>
    )
  }

  return (
    <section aria-label="Telemetry windows">
      <div className="section-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
        <div className="section-title">
          📊 Aggregated Windows
          <span className="section-badge">
            {sorted.length} {sorted.length === telemetry.length ? 'rows' : `of ${telemetry.length} rows`}
          </span>
          {(newData || recentlyAddedKeys.size > 0) && (
            <span className="data-adding-indicator">
              <span className="pulse-beacon"></span>
              New data added {recentlyAddedKeys.size > 0 ? `(${recentlyAddedKeys.size} windows)` : ''}
            </span>
          )}
        </div>

        {availableBatches.length > 0 && (
          <div className="batch-filter-group" role="group" aria-label="Filter by Batch">
            <span className="batch-filter-title">Batch:</span>
            <button
              type="button"
              className={`batch-filter-btn ${selectedBatch === 'all' ? 'active' : ''}`}
              onClick={() => setSelectedBatch('all')}
            >
              All ({telemetry.length})
            </button>
            {availableBatches.map(b => {
              const count = telemetry.filter(r => r.batch_id === b).length
              return (
                <button
                  key={b}
                  type="button"
                  className={`batch-filter-btn ${selectedBatch === b ? 'active' : ''}`}
                  onClick={() => setSelectedBatch(b)}
                >
                  Batch {b} ({count})
                </button>
              )
            })}
          </div>
        )}
      </div>
      <div className="table-wrapper">
        <table className="telemetry-table" id="telemetry-table">
          <thead>
            <tr>
              {COLUMNS.map(col => (
                <th
                  key={col.key}
                  className={sortKey === col.key ? 'sorted' : ''}
                  onClick={() => handleSort(col.key)}
                  aria-sort={sortKey === col.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
                >
                  {col.label}
                  {arrowIcon(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => {
              const status = deriveStatus(row)
              const rowKey = `${row.vehicle_id}-${row.window_start}`
              const isNew = recentlyAddedKeys.has(rowKey)
              return (
                <tr
                  key={`${rowKey}-${i}`}
                  className={`${status.level === 'fault' ? 'row-fault' : ''} ${isNew ? 'row-new-entry' : ''}`.trim()}
                >
                  <td>
                    <span className="batch-badge">
                      {row.batch_id !== undefined && row.batch_id !== null ? `Batch ${row.batch_id}` : '—'}
                    </span>
                  </td>
                  <td><span className="vehicle-id">{row.vehicle_id}</span></td>
                  <td>{formatTimestamp(row.window_start)}</td>
                  <td>{formatTimestamp(row.window_end)}</td>
                  <td>{round(row.average_speed, 1)} <small style={{color:'var(--color-text-muted)'}}>km/h</small></td>
                  <td>{round(row.average_battery_level, 1)} <small style={{color:'var(--color-text-muted)'}}>%</small></td>
                  <td>{round(row.maximum_temperature, 1)} <small style={{color:'var(--color-text-muted)'}}>°C</small></td>
                  <td style={{color: row.fault_count > 0 ? 'var(--color-error)' : 'var(--color-success)', fontWeight: 600}}>
                    {row.fault_count}
                  </td>
                  <td>{row.event_count}</td>
                  <td>
                    <span className={`status-chip ${status.level}`}>
                      {status.level === 'ok' ? '✓' : status.level === 'fault' ? '✕' : '△'}
                      {status.label}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
