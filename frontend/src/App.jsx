import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import PropuestaWizard from './features/propuesta/components/PropuestaWizard'
import CronogramaForm from './features/cronograma/components/CronogramaForm'
import BgCanvas from './components/BgCanvas'
import Bot3D from './components/Bot3D'
import ChatBotPanel from './features/ai/components/ChatBotPanel'
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
  const [chatOpen, setChatOpen] = useState(true)
  const [proposalDraft, setProposalDraft] = useState(null)
  const [reviewRequested, setReviewRequested] = useState(false)

  const handleDraftGenerated = (draft) => {
    setProposalDraft(draft)
    setReviewRequested(false)
  }

  const handleProposalModified = (draft) => {
    setProposalDraft(draft)
    setReviewRequested(true)
    setChatOpen(true)
  }

  return (
    <BrowserRouter>
      <BgCanvas />
      <Bot3D onToggleChat={() => setChatOpen((current) => !current)} />
      <ChatBotPanel
        open={chatOpen}
        onToggle={() => setChatOpen((current) => !current)}
        proposalDraft={proposalDraft}
        onProposalModified={handleProposalModified}
      />
      <Routes>
        <Route
          path="/"
          element={
            <PropuestaWizard
              onDraftGenerated={handleDraftGenerated}
              proposalDraft={proposalDraft}
              reviewRequested={reviewRequested}
              onOpenChat={() => setChatOpen(true)}
            />
          }
        />
        <Route path="/cronograma" element={<CronogramaPage />} />
      </Routes>
    </BrowserRouter>
  )
}
