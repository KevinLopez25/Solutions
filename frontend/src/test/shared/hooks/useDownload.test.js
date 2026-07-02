import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useDownload } from '../../../shared/hooks/useDownload'

describe('useDownload', () => {
  let createElementSpy, revokeSpy

  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:test')
    URL.revokeObjectURL = vi.fn()

    const mockAnchor = document.createElement('a')
    const clickSpy = vi.spyOn(mockAnchor, 'click').mockImplementation(() => {})

    createElementSpy = vi.spyOn(document, 'createElement').mockImplementation(() => mockAnchor)
    revokeSpy = vi.spyOn(URL, 'revokeObjectURL')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should create a download link and click it', () => {
    const { result } = renderHook(() => useDownload())
    const base64 = btoa('test content')

    result.current.download(base64, 'test.pptx', 'application/ppt')

    expect(createElementSpy).toHaveBeenCalledWith('a')
    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(revokeSpy).toHaveBeenCalledWith('blob:test')
  })
})