/**
 * Match either an exact section code or a dot-delimited child code.
 *
 * The dot boundary matters because a raw prefix match would make U1
 * incorrectly match codes such as U13.15.
 */
export function matchesSectionPrefix(
  sectionCode: string,
  prefixes: string[],
): boolean {
  return prefixes.some(
    (prefix) =>
      sectionCode === prefix || sectionCode.startsWith(`${prefix}.`),
  )
}