import { describe, expect, it } from 'vitest'

import { reassembleSectionText } from './chunk-text.js'

describe('reassembleSectionText', () => {
  it('joins chunks in chunk index order', () => {
    const result = reassembleSectionText([
      { chunk_index: 1, text: 'Second' },
      { chunk_index: 0, text: 'First' },
    ])

    expect(result).toBe('First\nSecond')
  })

  it('removes the duplicated overlap from adjacent chunks', () => {
    const overlap = 'A'.repeat(200)

    const result = reassembleSectionText([
      {
        chunk_index: 0,
        text: `First section text ${overlap}`,
      },
      {
        chunk_index: 1,
        text: `${overlap} continued section text`,
      },
    ])

    expect(result).toBe(
      `First section text ${overlap}\ncontinued section text`,
    )
  })

  it('preserves text when the next chunk does not contain the overlap', () => {
    const result = reassembleSectionText([
      { chunk_index: 0, text: 'First section' },
      { chunk_index: 1, text: 'Different section' },
    ])

    expect(result).toBe('First section\nDifferent section')
  })
})