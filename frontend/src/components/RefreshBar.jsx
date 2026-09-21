/**
 * RefreshBar — shows last refresh time, polling interval,
 * new-data indicator, and a manual refresh button.
 */
import { formatTime, formatInterval } from '../utils/formatters.js'

export default function RefreshBar({ lastRefreshed, newData, error, refreshInterval, onRefresh, loading }) {
  return (
    <div className="refresh-bar" id="refresh-bar" role="status" aria-live="polite">
      <div className="refresh-info">
        <span className="refresh-timestamp">
          Last refresh:{' '}
          <strong id="last-refresh-time">
            {lastRefreshed ? formatTime(lastRefreshed) : 'Pending…'}
          </strong>
        </span>

        <span className="refresh-interval-badge" title="Auto-refresh interval">
          ⏱ Auto-refresh: {formatInterval(refreshInterval)}
        </span>

        {newData && (
          <span className="new-data-badge" id="new-data-badge">
            ✦ New windows detected
          </span>
        )}
      </div>

      <div className="refresh-actions">
        <button
          className="btn btn-primary"
          id="refresh-btn"
          onClick={onRefresh}
          disabled={loading}
          aria-label="Refresh data now"
        >
          <span className={loading ? 'spin' : ''} aria-hidden="true">⟳</span>
          {loading ? 'Refreshing…' : 'Refresh Now'}
        </button>
      </div>
    </div>
  )
}
