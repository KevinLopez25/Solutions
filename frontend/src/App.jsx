import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import PropuestaWizard from './features/propuesta/components/PropuestaWizard'
import CronogramaForm from './features/cronograma/components/CronogramaForm'
import './assets/styles/global.css'

function NavBar() {
  return (
    <nav className="navbar">
      <span className="nav-brand">Solutions</span>
      <div className="nav-links">
        <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Propuesta</NavLink>
        <NavLink to="/cronograma" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Cronograma</NavLink>
      </div>
    </nav>
  )
}

function Layout() {
  const location = useLocation()
  const shellClass = location.pathname === '/cronograma' ? 'app-shell cronograma' : 'app-shell'

  return (
    <div className={shellClass}>
      <div className="app-background" aria-hidden="true">
        <div className="bg-grid" />
        <div className="glow-orb" />
        <div className="bot-hero" aria-hidden="true">
          <div className="bot-card">
            <div className="bot-head">
              <div className="bot-eye left" />
              <div className="bot-eye right" />
              <div className="bot-mouth" />
            </div>
            <div className="bot-body" />
            <div className="bot-antenna" />
          </div>
        </div>
        <div className="device-hero" aria-hidden="true">
          <div className="device-frame">
            <div className="device-screen">
              <div className="device-status" />
              <div className="device-lines">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="page-content">
        <NavBar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<PropuestaWizard />} />
            <Route path="/cronograma" element={<CronogramaForm />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout />
    </BrowserRouter>
  )
}
