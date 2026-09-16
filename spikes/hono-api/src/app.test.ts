import { afterAll, describe, expect, it } from 'vitest'

import { app } from './app.js'
import { db } from './db.js'
import type {
  BrowseCategory,
  SectionDetail,
} from './types/browse.js'

afterAll(async () => {
  await db.end()
})

describe('browse API', () => {
  it('returns browse categories', async () => {
    const response = await app.request('/browse/categories')

    expect(response.status).toBe(200)

    const body = await response.json() as BrowseCategory[]

    expect(body.length).toBeGreaterThan(0)
    expect(body[0].id).toBeTypeOf('string')
    expect(body[0].branches[0].section_count).toBeTypeOf('number')
  })

  it('returns the FastAPI-compatible 404 shape for an unknown group', async () => {
    const response = await app.request(
      '/browse/sections?group=does_not_exist',
    )

    expect(response.status).toBe(404)
    expect(await response.json()).toEqual({
      detail: 'Unknown group: does_not_exist',
    })
  })

  it('returns a section date exactly as stored in PostgreSQL', async () => {
    const response = await app.request('/browse/sections/SR3.15')

    expect(response.status).toBe(200)

    const body = await response.json() as SectionDetail

    const databaseResult = await db.query<{
      effective_date: string | null
    }>(
      `
        SELECT effective_date::text AS effective_date
        FROM sections
        WHERE section_code = $1
      `,
      ['SR3.15'],
    )

    expect(body.effective_date).toBe(
      databaseResult.rows[0].effective_date,
    )
  })
})