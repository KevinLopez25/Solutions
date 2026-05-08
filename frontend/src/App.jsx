import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import PropuestaWizard from './features/propuesta/components/PropuestaWizard'
import CronogramaForm from './features/cronograma/components/CronogramaForm'
import BgCanvas from './components/BgCanvas'
import Bot3D from './components/Bot3D'
import AgentChat from './components/AgentChat'
import './assets/styles/global.css'

function CronogramaPage() {
  return (
    <div className="crono-page">
      <div className="crono-topbar">
        <Link to="/" className="crono-back">← Propuesta</Link>
        <span className="crono-brand">Solutions — Cronograma</span>
      </div>
      <div className="crono-main">
        <CronogramaForm />
      </div>
    </div>
  )
}

export default function App() {
  const [chatOpen, setChatOpen] = useState(false)

  return (
    <BrowserRouter>
      <BgCanvas />
      <Bot3D onToggle={() => setChatOpen(v => !v)} isActive={chatOpen} />
      <AgentChat isOpen={chatOpen} onClose={() => setChatOpen(false)} />
      <Routes>
        <Route path="/" element={<PropuestaWizard />} />
        <Route path="/cronograma" element={<CronogramaPage />} />
      </Routes>
    </BrowserRouter>
  )
}
