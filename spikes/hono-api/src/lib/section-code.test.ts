import { describe, expect, it } from 'vitest'

import { matchesSectionPrefix } from './section-code.js'

describe('matchesSectionPrefix', () => {
  it('matches an exact section code', () => {
    expect(matchesSectionPrefix('U13', ['U13'])).toBe(true)
  })

  it('matches a dot-delimited child section', () => {
    expect(matchesSectionPrefix('U13.15', ['U13'])).toBe(true)
  })

  it('does not match a similar prefix without a dot boundary', () => {
    expect(matchesSectionPrefix('U13.15', ['U1'])).toBe(false)
  })

  it('matches when any supplied prefix applies', () => {
    expect(matchesSectionPrefix('SR3.15', ['SR1', 'SR2', 'SR3'])).toBe(true)
  })
})