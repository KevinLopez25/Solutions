import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CatalogoForm from '../../../../features/catalogo/components/CatalogoForm'

describe('CatalogoForm', () => {
  const fields = [
    { key: 'nombre', label: 'Nombre', type: 'text', required: true },
    { key: 'descripcion', label: 'Descripción', type: 'textarea' },
  ]

  it('should render fields with labels', () => {
    render(<CatalogoForm fields={fields} onSubmit={() => {}} />)
    expect(screen.getByText('Nombre')).toBeInTheDocument()
    expect(screen.getByText('Descripción')).toBeInTheDocument()
  })

  it('should render input for text type', () => {
    render(<CatalogoForm fields={fields} onSubmit={() => {}} />)
    expect(screen.getByLabelText('Nombre')).toBeInTheDocument()
  })

  it('should render textarea for textarea type', () => {
    render(<CatalogoForm fields={fields} onSubmit={() => {}} />)
    expect(screen.getByLabelText('Descripción')).toBeInTheDocument()
  })

  it('should render submit button with default label', () => {
    render(<CatalogoForm fields={fields} onSubmit={() => {}} />)
    expect(screen.getByRole('button', { name: 'Guardar' })).toBeInTheDocument()
  })

  it('should render submit button with custom label', () => {
    render(<CatalogoForm fields={fields} onSubmit={() => {}} submitLabel="Crear" />)
    expect(screen.getByRole('button', { name: 'Crear' })).toBeInTheDocument()
  })

  it('should call onSubmit with values when form is submitted', async () => {
    const handleSubmit = vi.fn()
    render(<CatalogoForm fields={fields} onSubmit={handleSubmit} />)

    await userEvent.type(screen.getByLabelText('Nombre'), 'Torre IA')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(handleSubmit).toHaveBeenCalledWith(expect.objectContaining({ nombre: 'Torre IA', descripcion: '' }))
  })

  it('should clear fields after submit', async () => {
    const handleSubmit = vi.fn()
    render(<CatalogoForm fields={fields} onSubmit={handleSubmit} />)

    const input = screen.getByLabelText('Nombre')
    await userEvent.type(input, 'Test')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(input).toHaveValue('')
  })

  it('should handle empty fields array', () => {
    render(<CatalogoForm fields={[]} onSubmit={() => {}} />)
    expect(screen.getByRole('button', { name: 'Guardar' })).toBeInTheDocument()
  })

  it('should use default value for field when provided', () => {
    const fieldsWithDefault = [
      { key: 'nombre', label: 'Nombre', type: 'text', default: 'Default Value' },
    ]
    render(<CatalogoForm fields={fieldsWithDefault} onSubmit={() => {}} />)
    expect(screen.getByLabelText('Nombre')).toHaveValue('Default Value')
  })
})