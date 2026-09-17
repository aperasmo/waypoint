export type BrowseBranch = {
  label: string
  section_count: number
}

export type BrowseCategory = {
  id: string
  label: string
  description: string
  branches: BrowseBranch[]
}

export type TaxonomyBranch = {
  label: string
  prefixes: string[]
  note: string
}

export type TaxonomyGroup = {
  id: string
  label: string
  description: string
  prefixes: string[]
  branches: TaxonomyBranch[]
}

export type BrowseTaxonomy = {
  _note: string
  groups: TaxonomyGroup[]
}

export type SectionSummary = {
  section_code: string
  title: string
  effective_date: string | null
}

export type SectionDetail = {
  section_code: string
  title: string
  source_url: string
  effective_date: string | null
  text: string
}