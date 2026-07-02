import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'

// Mock the heavy components that use canvas/3D
vi.mock('../components/BgCanvas', () => ({
  default: () => <div data-testid="bg-canvas" />,
}))

vi.mock('../components/Bot3D', () => ({
  default: ({ onToggleChat }) => (
    <button data-testid="bot3d" onClick={onToggleChat}>Bot3D</button>
  ),
}))

vi.mock('../features/ai/components/ChatBotPanel', () => ({
  default: ({ open, onToggle }) => (
    <div data-testid="chat-panel" data-open={open}>
      <button onClick={onToggle}>Toggle Chat</button>
    </div>
  ),
}))

vi.mock('../features/propuesta/components/PropuestaWizard', () => ({
  default: ({ onDraftGenerated, proposalDraft, reviewRequested, onOpenChat }) => (
    <div data-testid="propuesta-wizard" data-has-draft={!!proposalDraft} data-review={reviewRequested}>
      <button data-testid="generate-draft" onClick={() => onDraftGenerated({ id: 1, content: 'test' })}>
        Generate Draft
      </button>
      <button onClick={onOpenChat}>Open Chat</button>
    </div>
  ),
}))

vi.mock('../features/cronograma/components/CronogramaForm', () => ({
  default: () => <div data-testid="cronograma-form" />,
}))

describe('App', () => {
  it('should render the main page with PropuestaWizard at default route "/"', () => {
    render(<App />)

    expect(screen.getByTestId('bg-canvas')).toBeInTheDocument()
    expect(screen.getByTestId('bot3d')).toBeInTheDocument()
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
    expect(screen.getByTestId('propuesta-wizard')).toBeInTheDocument()
  })

  it('should start with chat open by default', () => {
    render(<App />)

    const chatPanel = screen.getByTestId('chat-panel')
    expect(chatPanel).toHaveAttribute('data-open', 'true')
  })

  it('should toggle chat visibility when Bot3D button is clicked', async () => {
    render(<App />)

    const chatPanel = screen.getByTestId('chat-panel')
    expect(chatPanel).toHaveAttribute('data-open', 'true')

    await userEvent.click(screen.getByTestId('bot3d'))

    await waitFor(() => {
      expect(chatPanel).toHaveAttribute('data-open', 'false')
    })
  })

  it('should update proposalDraft when draft is generated', async () => {
    render(<App />)

    const wizard = screen.getByTestId('propuesta-wizard')
    expect(wizard).toHaveAttribute('data-has-draft', 'false')

    await userEvent.click(screen.getByTestId('generate-draft'))

    await waitFor(() => {
      expect(wizard).toHaveAttribute('data-has-draft', 'true')
    })
  })
})