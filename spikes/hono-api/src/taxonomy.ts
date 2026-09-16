import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import type { BrowseTaxonomy } from './types/browse.js'

const currentDir = path.dirname(fileURLToPath(import.meta.url))

// Resolve from this module rather than process.cwd() so the service works
// regardless of which directory the Node process was launched from.
const taxonomyPath = path.resolve(
  currentDir,
  '../../../data/categories.json',
)

let cachedTaxonomy: BrowseTaxonomy | null = null

export async function getTaxonomy(): Promise<BrowseTaxonomy> {
  if (cachedTaxonomy) {
    return cachedTaxonomy
  }

  const raw = await readFile(taxonomyPath, 'utf-8')
  cachedTaxonomy = JSON.parse(raw) as BrowseTaxonomy

  return cachedTaxonomy
}