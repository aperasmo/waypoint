import { ChevronRight } from "lucide-react"
import { Link } from "react-router-dom"

/**
 * Builds a Browse URL from the navigation state supplied to it.
 *
 * URLSearchParams handles spaces and other characters safely, which is
 * important because branch names are human-readable labels.
 */
function buildBrowseUrl(params) {
  const searchParams = new URLSearchParams(params)

  return `/browse?${searchParams.toString()}`
}

/**
 * Shows the user's current location within the Browse hierarchy.
 *
 * Previous levels are links so users can move back without relying on the
 * browser Back button. The current level is plain text because it represents
 * the page the user is already viewing.
 */
function BrowseBreadcrumbs({
  group,
  branchLabel = null,
  sectionCode = null,
}) {
  // A breadcrumb containing only "Browse" adds little value on the root page.
  if (!group) {
    return null
  }

  const groupUrl = buildBrowseUrl({
    group: group.id,
  })

  const branchUrl = branchLabel
    ? buildBrowseUrl({
        group: group.id,
        branch: branchLabel,
      })
    : null

  return (
    <nav
      className="mt-7"
      aria-label="Browse breadcrumb"
    >
      <ol className="flex flex-wrap items-center gap-2 text-sm">
        <li>
          <Link
            to="/browse"
            className="font-medium text-waypoint-blue hover:underline"
          >
            Browse
          </Link>
        </li>

        <li aria-hidden="true">
          <ChevronRight className="size-4 text-muted-foreground" />
        </li>

        <li>
          {branchLabel ? (
            <Link
              to={groupUrl}
              className="font-medium text-waypoint-blue hover:underline"
            >
              {group.label}
            </Link>
          ) : (
            <span
              className="text-muted-foreground"
              aria-current="page"
            >
              {group.label}
            </span>
          )}
        </li>

        {branchLabel && (
          <>
            <li aria-hidden="true">
              <ChevronRight className="size-4 text-muted-foreground" />
            </li>

            <li>
              {sectionCode ? (
                <Link
                  to={branchUrl}
                  className="font-medium text-waypoint-blue hover:underline"
                >
                  {branchLabel}
                </Link>
              ) : (
                <span
                  className="text-muted-foreground"
                  aria-current="page"
                >
                  {branchLabel}
                </span>
              )}
            </li>
          </>
        )}

        {sectionCode && (
          <>
            <li aria-hidden="true">
              <ChevronRight className="size-4 text-muted-foreground" />
            </li>

            <li>
              <span
                className="text-muted-foreground"
                aria-current="page"
              >
                {sectionCode}
              </span>
            </li>
          </>
        )}
      </ol>
    </nav>
  )
}

export default BrowseBreadcrumbs