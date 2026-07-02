import { describe, it, expect } from 'vitest'
import {
  FILIALES,
  FILIAL_LABELS,
  FILIAL_CODES,
  PILLS,
  PILL_LABELS,
  TORRES_ALL,
  TORRE_ICONS,
  TORRE_RESUMEN_MAP,
} from '../../core/constants'

describe('Constants', () => {
  describe('FILIALES', () => {
    it('should contain the three filiales', () => {
      expect(FILIALES).toEqual(['corp', 'group', 'cbit'])
    })
  })

  describe('FILIAL_LABELS', () => {
    it('should have labels for all filiales', () => {
      expect(FILIAL_LABELS.corp).toBe('Periferia IT Corp')
      expect(FILIAL_LABELS.group).toBe('Periferia IT Group')
      expect(FILIAL_LABELS.cbit).toBe('Contact & Business IT')
    })
  })

  describe('FILIAL_CODES', () => {
    it('should have codes for all filiales', () => {
      expect(FILIAL_CODES.corp).toBe('PCIT')
      expect(FILIAL_CODES.group).toBe('PGIT')
      expect(FILIAL_CODES.cbit).toBe('CBIT')
    })
  })

  describe('PILLS', () => {
    it('should have all pill definitions', () => {
      const keys = PILLS.map(p => p.key)
      expect(keys).toContain('entregables')
      expect(keys).toContain('perfiles')
      expect(keys).toContain('consideraciones')
      expect(keys).toContain('fda')
    })

    it('each pill should have a key and label', () => {
      for (const pill of PILLS) {
        expect(pill).toHaveProperty('key')
        expect(pill).toHaveProperty('label')
        expect(typeof pill.key).toBe('string')
        expect(typeof pill.label).toBe('string')
      }
    })
  })

  describe('PILL_LABELS', () => {
    it('should have labels for all pill keys', () => {
      expect(PILL_LABELS.entregables).toBe('Entregables')
      expect(PILL_LABELS.perfiles).toBe('Perfiles')
      expect(PILL_LABELS.consideraciones).toBe('Consideraciones')
      expect(PILL_LABELS.fda).toBe('Fuera del Alcance')
    })
  })

  describe('TORRES_ALL', () => {
    it('should contain all tower names', () => {
      expect(TORRES_ALL).toContain('FULLSTACK / DESARROLLO')
      expect(TORRES_ALL).toContain('ARQUITECTURA')
      expect(TORRES_ALL).toContain('DATOS')
      expect(TORRES_ALL).toContain('IA')
      expect(TORRES_ALL).toContain('DEVOPS')
      expect(TORRES_ALL).toContain('CIBERSEGURIDAD')
    })

    it('should have 12 towers', () => {
      expect(TORRES_ALL).toHaveLength(12)
    })
  })

  describe('TORRE_ICONS', () => {
    it('should have icons for all towers', () => {
      for (const torre of TORRES_ALL) {
        expect(TORRE_ICONS).toHaveProperty(torre)
        expect(typeof TORRE_ICONS[torre]).toBe('string')
      }
    })
  })

  describe('TORRE_RESUMEN_MAP', () => {
    it('should map full tower names to short names', () => {
      expect(TORRE_RESUMEN_MAP['Torre Full Stack']).toBe('FULLSTACK / DESARROLLO')
      expect(TORRE_RESUMEN_MAP['Torre Data']).toBe('DATOS')
      expect(TORRE_RESUMEN_MAP['Torre IA']).toBe('IA')
      expect(TORRE_RESUMEN_MAP['Torre DevOps']).toBe('DEVOPS')
    })

    it('should handle both spellings of Integración', () => {
      expect(TORRE_RESUMEN_MAP['Torre Integración']).toBe('INTEGRACIÓN')
      expect(TORRE_RESUMEN_MAP['Torre Integracion']).toBe('INTEGRACIÓN')
    })
  })
})