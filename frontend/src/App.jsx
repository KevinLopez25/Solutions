import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import PropuestaWizard from './features/propuesta/components/PropuestaWizard'
import CronogramaForm from './features/cronograma/components/CronogramaForm'
import './assets/styles/global.css'

function NavBar() {
  return (
    <nav className="navbar">
      <span className="nav-brand">Solutions</span>
      <div className="nav-links">
        <NavLink to="/"          className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Propuesta</NavLink>
        <NavLink to="/cronograma" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Cronograma</NavLink>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <main className="main-content">
        <Routes>
          <Route path="/"           element={<PropuestaWizard />} />
          <Route path="/cronograma" element={<CronogramaForm />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
