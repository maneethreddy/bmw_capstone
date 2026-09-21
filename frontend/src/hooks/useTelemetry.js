/**
 * useTelemetry — custom React hook
 *
 * Polls the FastAPI backend at a configurable interval and exposes:
 *   - telemetry    : latest aggregated windows from /api/telemetry
 *   - summary      : fleet KPIs from /api/summary
 *   - faults       : fault windows from /api/faults
 *   - apiStatus    : 'online' | 'offline' | 'checking'
 *   - errorType    : null | 'network' | 'aws_access_denied' | 'athena_query_failed'
 *   - loading      : true on first load
 *   - error        : user-facing error message (null if none)
 *   - lastRefreshed: Date of last successful fetch
 *   - newData      : true for 2 seconds after new windows are detected
 *   - refresh      : function to trigger an immediate refresh
 *
 * NOTE: This hook fetches from VITE_API_BASE_URL (the FastAPI server).
 * It never contacts AWS directly. No AWS credentials are present in this file.
 *
 * Error classification:
 *   - fetch() throws (network error / DNS / refused) → errorType 'network'
 *   - HTTP 503 with detail.error_type 'aws_access_denied'  → errorType 'aws_access_denied'
 *   - HTTP 503 with detail.error_type 'athena_query_failed' → errorType 'athena_query_failed'
 *   - Any other non-2xx status                             → errorType 'athena_query_failed'
 *
 * The raw detail string from FastAPI is NEVER forwarded to the UI.
 * Only the user-facing messages defined here reach the browser.
 */

import { useState, useEffect, useCallback, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const INTERVAL  = parseInt(import.meta.env.VITE_REFRESH_INTERVAL || '10000', 10)

// User-facing messages — no AWS internals, credentials, or account IDs
const ERROR_MESSAGES = {
  network:             'Cannot reach the API server.',
  aws_access_denied:   'Athena query access denied. Check AWS IAM permissions.',
  athena_query_failed: 'Athena query execution failed.',
}

/**
 * Fetches a JSON endpoint and throws a structured error on failure.
 * The thrown error always has:
 *   error.errorType : one of the ERROR_MESSAGES keys
 *   error.message   : the user-facing string (never raw AWS details)
 */
async function fetchJSON(path) {
  let resp
  try {
    resp = await fetch(`${API_BASE}${path}`)
  } catch {
    // Network failure (offline, DNS failure, CORS, refused)
    const err = new Error(ERROR_MESSAGES.network)
    err.errorType = 'network'
    throw err
  }

  if (resp.ok) return resp.json()

  // Non-2xx: try to read the FastAPI error body to classify the failure
  let errorType = 'athena_query_failed'
  try {
    const body = await resp.json()
    // FastAPI wraps HTTPException detail as { detail: <value> }
    const detail = body?.detail
    if (detail && typeof detail === 'object' && detail.error_type) {
      errorType = detail.error_type === 'aws_access_denied'
        ? 'aws_access_denied'
        : 'athena_query_failed'
    }
  } catch {
    // Body was not JSON — keep default errorType
  }

  const err = new Error(ERROR_MESSAGES[errorType] ?? ERROR_MESSAGES.athena_query_failed)
  err.errorType = errorType
  throw err
}

export function useTelemetry() {
  const [telemetry, setTelemetry]         = useState([])
  const [summary, setSummary]             = useState(null)
  const [faults, setFaults]               = useState([])
  const [apiStatus, setApiStatus]         = useState('checking')
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState(null)
  const [errorType, setErrorType]         = useState(null)
  const [lastRefreshed, setLastRefreshed] = useState(null)
  const [newData, setNewData]             = useState(false)

  // Track previous window count to detect new arrivals
  const prevWindowCount = useRef(0)
  const newDataTimer    = useRef(null)

  const fetchAll = useCallback(async () => {
    try {
      const [tel, sum, flt] = await Promise.all([
        fetchJSON('/api/telemetry'),
        fetchJSON('/api/summary'),
        fetchJSON('/api/faults'),
      ])

      // Detect new windows
      if (prevWindowCount.current > 0 && sum.total_windows > prevWindowCount.current) {
        clearTimeout(newDataTimer.current)
        setNewData(true)
        newDataTimer.current = setTimeout(() => setNewData(false), 3000)
      }
      prevWindowCount.current = sum.total_windows

      setTelemetry(tel)
      setSummary(sum)
      setFaults(flt)
      setApiStatus('online')
      setError(null)
      setErrorType(null)
      setLastRefreshed(new Date())
    } catch (err) {
      // errorType is 'network' when FastAPI is unreachable;
      // 'aws_access_denied' or 'athena_query_failed' when FastAPI is up but AWS fails.
      const type = err.errorType ?? 'network'
      setApiStatus(type === 'network' ? 'offline' : 'degraded')
      setError(err.message)
      setErrorType(type)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const timer = setInterval(fetchAll, INTERVAL)
    return () => {
      clearInterval(timer)
      clearTimeout(newDataTimer.current)
    }
  }, [fetchAll])

  return {
    telemetry,
    summary,
    faults,
    apiStatus,
    loading,
    error,
    errorType,
    lastRefreshed,
    newData,
    refresh: fetchAll,
    refreshInterval: INTERVAL,
  }
}
