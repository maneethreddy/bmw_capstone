import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function PipelineControls() {
  const [loadingAction, setLoadingAction] = useState(null) // 'kafka' | 'spark' | 'generate' | null
  const [feedback, setFeedback] = useState(null) // { type: 'success' | 'error', message: string, command?: string }

  const runCommand = async (action, endpoint, defaultCommand) => {
    setLoadingAction(action)
    setFeedback(null)

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })

      const data = await res.json()

      if (!res.ok) {
        const errorText =
          data?.detail?.error ||
          data?.detail?.message ||
          data?.error ||
          data?.message ||
          `Command failed with HTTP ${res.status}`
        throw new Error(errorText)
      }

      setFeedback({
        type: 'success',
        message: data.output || data.message || 'Command executed successfully.',
        command: data.command || defaultCommand,
      })
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to execute command.',
        command: defaultCommand,
      })
    } finally {
      setLoadingAction(null)
    }
  }

  return (
    <section className="terminal-controls-section" aria-label="Pipeline Terminal Controls">
      <div className="terminal-controls-bar">
        <button
          className="btn-terminal btn-terminal-kafka"
          id="btn-start-kafka"
          disabled={loadingAction !== null}
          onClick={() =>
            runCommand(
              'kafka',
              '/api/pipeline/start-kafka',
              'docker compose up -d kafka'
            )
          }
        >
          {loadingAction === 'kafka' ? (
            <>
              <span className="btn-spinner" /> Starting Kafka…
            </>
          ) : (
            '▶ START KAFKA'
          )}
        </button>

        <button
          className="btn-terminal btn-terminal-spark"
          id="btn-start-spark"
          disabled={loadingAction !== null}
          onClick={() =>
            runCommand(
              'spark',
              '/api/pipeline/start-spark',
              'python -m src.streaming.run_streaming --window-duration "1 minute" --watermark-delay "30 seconds" --checkpoint ./checkpoints/demo'
            )
          }
        >
          {loadingAction === 'spark' ? (
            <>
              <span className="btn-spinner" /> Starting Spark…
            </>
          ) : (
            '▶ START SPARK'
          )}
        </button>

        <button
          className="btn-terminal btn-terminal-generate"
          id="btn-generate-data"
          disabled={loadingAction !== null}
          onClick={() =>
            runCommand(
              'generate',
              '/api/pipeline/generate-data',
              'python -m src.generator.cli --count 20 --interval 0.2'
            )
          }
        >
          {loadingAction === 'generate' ? (
            <>
              <span className="btn-spinner" /> Generating Data…
            </>
          ) : (
            '⚡ GENERATE DATA'
          )}
        </button>
      </div>

      {feedback && (
        <div
          className={`terminal-feedback feedback-${feedback.type}`}
          role={feedback.type === 'error' ? 'alert' : 'status'}
          id="terminal-command-feedback"
        >
          <span className="feedback-icon">
            {feedback.type === 'success' ? '✓' : '✗'}
          </span>
          <div className="feedback-body">
            <div className="feedback-command">
              <code>$ {feedback.command}</code>
            </div>
            <div className="feedback-message">{feedback.message}</div>
          </div>
        </div>
      )}
    </section>
  )
}
