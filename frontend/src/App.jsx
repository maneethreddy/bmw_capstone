/**
 * App — root component.
 *
 * Wires together the useTelemetry hook (polling FastAPI) with all dashboard
 * sections. * Layout order:
 *   1. Header (brand + pipeline status)
 *   2. Refresh bar (last refresh, interval, new-data indicator)
 *   3. Pipeline flow strip
 *   4. Summary KPI cards
 *   5. Detailed windows table
 *   6. Fault panel
 */
import { useTelemetry }    from './hooks/useTelemetry.js'
import Header              from './components/Header.jsx'
import RefreshBar          from './components/RefreshBar.jsx'
import PipelineControls    from './components/PipelineControls.jsx'
import PipelineStatus      from './components/PipelineStatus.jsx'
import SummaryCards        from './components/SummaryCards.jsx'
import FaultPanel          from './components/FaultPanel.jsx'
import TelemetryTable      from './components/TelemetryTable.jsx'

export default function App() {
  const {
    telemetry, summary, faults,
    apiStatus, loading, error,
    lastRefreshed, newData,
    refresh, refreshInterval,
  } = useTelemetry()

  return (
    <div className="app" id="app">
      <Header apiStatus={apiStatus} />

      <main className="main-content" id="main-content">

        {/* Refresh status */}
        <RefreshBar
          lastRefreshed={lastRefreshed}
          newData={newData}
          error={error}
          refreshInterval={refreshInterval}
          onRefresh={refresh}
          loading={loading}
        />

        {/* 3 Terminal-Equivalent Pipeline Controls */}
        <PipelineControls />

        {/* Pipeline flow */}
        <PipelineStatus apiStatus={apiStatus} />

        {/* Fleet KPI summary */}
        <SummaryCards summary={summary} loading={loading} />

        {/* Detailed windows table (Aggregated Windows) */}
        <TelemetryTable telemetry={telemetry} loading={loading} newData={newData} />

        {/* Fault monitoring */}
        <FaultPanel faults={faults} summary={summary} loading={loading} />

      </main>

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid rgba(255,255,255,0.05)',
        padding: '16px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '0.72rem',
        color: 'var(--color-text-muted)',
        background: 'rgba(8,13,30,0.5)',
        backdropFilter: 'blur(12px)',
        flexWrap: 'wrap',
        gap: '8px',
      }}>
        <span>BMW Connected Mobility · Capstone P11</span>
      </footer>
    </div>
  )
}
