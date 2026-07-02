import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Toggle from '../../../shared/components/Toggle'

describe('Toggle', () => {
  it('should render with label', () => {
    render(<Toggle label="Incluir QA" checked={false} onChange={() => {}} />)
    expect(screen.getByText('Incluir QA')).toBeInTheDocument()
  })

  it('should have "on" class when checked', () => {
    render(<Toggle label="Test" checked={true} onChange={() => {}} />)
    const toggle = screen.getByText('Test').nextElementSibling
    expect(toggle).toHaveClass('on')
    expect(toggle).not.toHaveClass('off')
  })

  it('should have "off" class when not checked', () => {
    render(<Toggle label="Test" checked={false} onChange={() => {}} />)
    const toggle = screen.getByText('Test').nextElementSibling
    expect(toggle).toHaveClass('off')
    expect(toggle).not.toHaveClass('on')
  })

  it('should call onChange when clicked', async () => {
    const handleChange = vi.fn()
    render(<Toggle label="Click me" checked={false} onChange={handleChange} />)
    const toggle = screen.getByText('Click me').nextElementSibling
    await userEvent.click(toggle)
    expect(handleChange).toHaveBeenCalledTimes(1)
  })
})