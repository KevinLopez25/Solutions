import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PillsControl from '../../../../features/propuesta/components/PillsControl'

describe('PillsControl', () => {
  const defaultOpciones = {
    entregables: false,
    perfiles: false,
    consideraciones: false,
    fda: false,
  }

  it('should render all sections', () => {
    render(<PillsControl opciones={defaultOpciones} onToggle={() => {}} incluirQa={false} onToggleQa={() => {}} excelVacio={false} />)
    expect(screen.getByText('Entregables')).toBeInTheDocument()
    expect(screen.getByText('Perfiles')).toBeInTheDocument()
    expect(screen.getByText('Consideraciones')).toBeInTheDocument()
    expect(screen.getByText('Fuera del Alcance')).toBeInTheDocument()
    expect(screen.getByText('Incluir QA')).toBeInTheDocument()
  })

  it('should call onToggle when a pill is clicked', async () => {
    const handleToggle = vi.fn()
    render(<PillsControl opciones={defaultOpciones} onToggle={handleToggle} incluirQa={false} onToggleQa={() => {}} excelVacio={false} />)

    const firstPill = screen.getByText('Entregables').closest('.srow').querySelector('.pill')
    await userEvent.click(firstPill)
    expect(handleToggle).toHaveBeenCalledWith('entregables')
  })

  it('should call onToggleQa when QA pill is clicked', async () => {
    const handleToggleQa = vi.fn()
    render(<PillsControl opciones={defaultOpciones} onToggle={() => {}} incluirQa={false} onToggleQa={handleToggleQa} excelVacio={false} />)

    const qaPill = screen.getAllByText('NO')[4].closest('.pill')
    await userEvent.click(qaPill)
    expect(handleToggleQa).toHaveBeenCalled()
  })

  it('should show active tags when sections are enabled', () => {
    const opcionesActivas = { ...defaultOpciones, entregables: true, perfiles: true }
    render(<PillsControl opciones={opcionesActivas} onToggle={() => {}} incluirQa={true} onToggleQa={() => {}} excelVacio={false} />)

    const mtagElements = document.querySelectorAll('.mtag')
    expect(mtagElements.length).toBe(3)
    expect(mtagElements[0].textContent).toBe('Entregables')
    expect(mtagElements[1].textContent).toBe('Perfiles')
    expect(mtagElements[2].textContent).toBe('QA')
  })

  it('should show placeholder when no sections are active', () => {
    render(<PillsControl opciones={defaultOpciones} onToggle={() => {}} incluirQa={false} onToggleQa={() => {}} excelVacio={false} />)

    expect(screen.getByText('Ninguna sección con genéricos')).toBeInTheDocument()
  })

  it('should apply "is-yes" class to active sections', () => {
    const opcionesActivas = { ...defaultOpciones, entregables: true }
    render(<PillsControl opciones={opcionesActivas} onToggle={() => {}} incluirQa={false} onToggleQa={() => {}} excelVacio={false} />)

    const rows = document.querySelectorAll('.srow')
    expect(rows[0].classList.contains('is-yes')).toBe(true)
    expect(rows[1].classList.contains('is-yes')).toBe(false)
  })
})