import { fetchJson } from "@/api/client"

/**
 * Loads the human-facing browse taxonomy with live database section counts.
 *
 * @param {AbortSignal} [signal] - Optional signal for cancelling the request.
 * @returns {Promise<Array>} Browse groups and their branches.
 */
export async function getBrowseCategories(signal) {
  return fetchJson("/browse/categories", {
    signal,
  })
}

/**
 * Loads section summaries for a selected group and optional branch.
 *
 * The backend requires a group before a branch can be applied, so this
 * function only sends branch when group is also present.
 *
 * @param {{ group?: string, branch?: string, signal?: AbortSignal }} options
 * @returns {Promise<Array>} Matching section summaries.
 */
export async function getBrowseSections({
  group,
  branch,
  signal,
} = {}) {
  const params = new URLSearchParams()

  if (group) {
    params.set("group", group)

    if (branch) {
      params.set("branch", branch)
    }
  }

  const query = params.toString()
  const path = query
    ? `/browse/sections?${query}`
    : "/browse/sections"

  return fetchJson(path, {
    signal,
  })
}

/**
 * Loads one complete indexed Operational Manual section.
 *
 * encodeURIComponent protects the URL when a section code contains
 * characters that have special meaning inside URLs.
 *
 * @param {string} sectionCode - Operational Manual section code.
 * @param {AbortSignal} [signal] - Optional signal for cancelling the request.
 * @returns {Promise<object>} Full section detail.
 */
export async function getBrowseSection(sectionCode, signal) {
  const encodedSectionCode = encodeURIComponent(sectionCode)

  return fetchJson(`/browse/sections/${encodedSectionCode}`, {
    signal,
  })
}