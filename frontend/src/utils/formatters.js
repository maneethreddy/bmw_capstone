/**
 * Formatting utilities for the BMW Capstone P11 dashboard.
 * Pure functions — no side effects, no AWS dependencies.
 */

/**
 * Round a numeric value to a given number of decimal places.
 * @param {number|string|null} value
 * @param {number} decimals
 * @returns {string}
 */
export function round(value, decimals = 1) {
  if (value === null || value === undefined || value === '') return '—'
  const n = parseFloat(value)
  if (isNaN(n)) return '—'
  return n.toFixed(decimals)
}

/**
 * Format a timestamp string to a human-readable local date-time.
 * Athena returns timestamps as "2026-09-17 10:00:00.000"
 * @param {string|null} ts
 * @returns {string}
 */
export function formatTimestamp(ts) {
  if (!ts) return '—'
  try {
    // Athena timestamps: "2026-09-17 10:00:00.000" — replace space with T for ISO parse
    const iso = ts.replace(' ', 'T')
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ts
    return d.toLocaleString(undefined, {
      month:  'short',
      day:    '2-digit',
      hour:   '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return ts
  }
}

/**
 * Format a Date object as a short time string.
 * @param {Date|null} date
 * @returns {string}
 */
export function formatTime(date) {
  if (!date) return '—'
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

/**
 * Derive the status of a telemetry window from its data.
 * Returns 'fault' | 'warning' | 'ok'
 * @param {{ fault_count: number, maximum_temperature: number, average_battery_level: number }} row
 * @returns {{ level: string, label: string }}
 */
export function deriveStatus(row) {
  const faults = parseInt(row.fault_count, 10) || 0
  const temp   = parseFloat(row.maximum_temperature) || 0
  const batt   = parseFloat(row.average_battery_level) || 100

  if (faults > 0) {
    return { level: 'fault', label: `${faults} Fault${faults > 1 ? 's' : ''}` }
  }
  if (temp > 90 || batt < 20) {
    return { level: 'warning', label: 'Warning' }
  }
  return { level: 'ok', label: 'Nominal' }
}

/**
 * Format a refresh interval (ms) as a human-readable string.
 * @param {number} ms
 * @returns {string}
 */
export function formatInterval(ms) {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${ms / 1000}s`
  return `${Math.round(ms / 60000)}m`
}
