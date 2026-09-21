/**
 * Header — BMW branding + pipeline status indicator.
 * Uses the real BMW logo from assets.
 */
import bmwLogo from '../assets/bmwlogo.jpg'

export default function Header({ apiStatus }) {
  const statusMap = {
    online:   { label: 'Live',        cls: 'online'   },
    offline:  { label: 'Offline',     cls: 'offline'  },
    degraded: { label: 'Degraded',    cls: 'offline'  },
    checking: { label: 'Connecting…', cls: 'checking' },
  }
  const { label, cls } = statusMap[apiStatus] || statusMap.checking

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo" aria-hidden="true">
          <img
            src={bmwLogo}
            alt="BMW Logo"
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              borderRadius: '50%',
              display: 'block',
            }}
          />
        </div>
        <div className="header-title">
          <h1>BMW Connected Mobility</h1>
          <span className="header-subtitle">
            Real-Time Vehicle Telemetry · Capstone P11
          </span>
        </div>
      </div>
    </header>
  )
}
