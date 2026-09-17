import { Hono } from 'hono'

import { db } from '../db.js'
import { matchesSectionPrefix } from '../lib/section-code.js'
import { getTaxonomy } from '../taxonomy.js'
import { reassembleSectionText } from '../lib/chunk-text.js'

import type {
  BrowseCategory,
  SectionDetail,
  SectionSummary,
} from '../types/browse.js'

type SectionCodeRow = {
  section_code: string
}

type SectionSummaryRow = {
  section_code: string
  title: string
  effective_date: string | null
}

type SectionDetailRow = {
  id: number
  section_code: string
  title: string
  source_url: string
  effective_date: string | null
}

type ChunkRow = {
  chunk_index: number
  text: string
}

export const browse = new Hono()

browse.get('/categories', async (c) => {
  const taxonomy = await getTaxonomy()

  // Counts come from the live database so the browse tree reflects the
  // sections that are actually available rather than taxonomy metadata alone.
  const result = await db.query<SectionCodeRow>(
    'SELECT section_code FROM sections',
  )

  const sectionCodes = result.rows.map((row) => row.section_code)

  const categories: BrowseCategory[] = taxonomy.groups.map((group) => ({
    id: group.id,
    label: group.label,
    description: group.description,
    branches: group.branches.map((branch) => ({
      label: branch.label,
      section_count: sectionCodes.filter((sectionCode) =>
        matchesSectionPrefix(sectionCode, branch.prefixes),
      ).length,
    })),
  }))

  return c.json(categories)
})

browse.get('/sections', async (c) => {
  const groupId = c.req.query('group')
  const branchLabel = c.req.query('branch')
  const taxonomy = await getTaxonomy()

  const result = await db.query<SectionSummaryRow>(`
    SELECT section_code, title, effective_date::text AS effective_date
    FROM sections
    ORDER BY section_code
  `)

  let sections = result.rows

  if (groupId) {
    const group = taxonomy.groups.find((item) => item.id === groupId)

    if (!group) {
      return c.json(
        { detail: `Unknown group: ${groupId}` },
        404,
      )
    }

    let branches = group.branches

    if (branchLabel) {
      branches = branches.filter(
        (branch) => branch.label === branchLabel,
      )

      if (branches.length === 0) {
        return c.json(
          { detail: `Unknown branch: ${branchLabel}` },
          404,
        )
      }
    }

    const prefixes = branches.flatMap((branch) => branch.prefixes)

    sections = sections.filter((section) =>
      matchesSectionPrefix(section.section_code, prefixes),
    )
  }

    const response: SectionSummary[] = sections.map((section) => ({
    section_code: section.section_code,
    title: section.title,
    effective_date: section.effective_date,
    }))

    return c.json(response)
})

browse.get('/sections/:sectionCode', async (c) => {
  const sectionCode = c.req.param('sectionCode')

  const sectionResult = await db.query<SectionDetailRow>(
    `
        SELECT
        id,
        section_code,
        title,
        source_url,
        effective_date::text AS effective_date
        FROM sections
        WHERE section_code = $1
    `,
    [sectionCode],
  )

  const section = sectionResult.rows[0]

  if (!section) {
    return c.json(
      { detail: `Unknown section: ${sectionCode}` },
      404,
    )
  }

  const chunkResult = await db.query<ChunkRow>(
    `
      SELECT chunk_index, text
      FROM chunks
      WHERE section_id = $1
      ORDER BY chunk_index
    `,
    [section.id],
  )

    const response: SectionDetail = {
    section_code: section.section_code,
    title: section.title,
    source_url: section.source_url,
    effective_date: section.effective_date,
    text: reassembleSectionText(chunkResult.rows),
    }

    return c.json(response)
})