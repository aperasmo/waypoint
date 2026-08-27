import { useEffect, useState } from "react"
import { ChevronRight, CircleAlert, FileText } from "lucide-react"

import { getBrowseSections } from "@/api/browse"
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

import { formatEffectiveDate } from "@/lib/utils"


/**
 * Loads and displays the Operational Manual sections belonging to one
 * selected browse branch.
 *
 * Filtering is performed by the backend. The frontend only requests and
 * presents the resulting section summaries.
 */
function BrowseSectionList({
  groupId,
  branch,
  selectedSection,
  onSectionSelect,
}) {
  const [sections, setSections] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const controller = new AbortController()

    /**
     * Reload the section list whenever the selected group or branch changes.
     *
     * The previous request is cancelled if the user navigates away before
     * it finishes.
     */
    async function loadSections() {
      setIsLoading(true)
      setError(null)
      setSections([])

      try {
        const data = await getBrowseSections({
          group: groupId,
          branch: branch.label,
          signal: controller.signal,
        })

        setSections(data)
      } catch (requestError) {
        if (requestError.name === "AbortError") {
          return
        }

        console.error(
          "Waypoint /browse/sections request failed:",
          requestError,
        )

        setError(
          "Waypoint could not load the sections for this area. Please try again.",
        )
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    loadSections()

    return () => {
      controller.abort()
    }
  }, [groupId, branch.label])

  return (
    <section aria-labelledby="browse-sections-heading">
      <p className="text-sm font-semibold text-waypoint-blue">
        {branch.label}
      </p>

      <h2
        id="browse-sections-heading"
        className="mt-1 text-xl font-semibold text-foreground"
      >
        Browse sections
      </h2>

      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
        {branch.section_count === 1
          ? "1 Operational Manual section is currently indexed in this area."
          : `${branch.section_count} Operational Manual sections are currently indexed in this area.`}
      </p>

      {/* Show a stable user-facing message if the section request fails. */}
      {error && (
        <Alert variant="destructive" className="mt-5">
          <CircleAlert className="size-4" />

          <AlertTitle>Sections could not be loaded</AlertTitle>

          <AlertDescription>
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* Reserve approximately the final layout while sections are loading. */}
      {isLoading && (
        <div className="mt-5 space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card key={index}>
              <CardContent className="flex items-center gap-4 p-4 sm:p-5">
                <Skeleton className="size-9 shrink-0 rounded-full" />

                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3 w-28" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Render the real section summaries returned by the backend. */}
      {!isLoading && !error && (
        <div className="mt-5 space-y-3">
          {sections.map((section) => {
            const isSelected =
              section.section_code === selectedSection

            const effectiveDate = formatEffectiveDate(
              section.effective_date,
            )

            return (
              <Card
                key={section.section_code}
                className={
                  isSelected
                    ? "border-waypoint-blue ring-1 ring-waypoint-blue"
                    : "transition-colors hover:border-waypoint-blue/50"
                }
              >
                <CardContent className="p-0">
                  <button
                    type="button"
                    onClick={() =>
                      onSectionSelect(section.section_code)
                    }
                    className="flex w-full items-start gap-4 p-4 text-left sm:p-5"
                    aria-pressed={isSelected}
                  >
                    <span
                      className="flex size-9 shrink-0 items-center justify-center rounded-full bg-waypoint-info-soft text-waypoint-info"
                      aria-hidden="true"
                    >
                      <FileText
                        className="size-4"
                        strokeWidth={1.8}
                      />
                    </span>

                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <Badge variant="secondary">
                          {section.section_code}
                        </Badge>

                        {effectiveDate && (
                          <span className="text-xs text-muted-foreground">
                            Effective {effectiveDate}
                          </span>
                        )}
                      </span>

                      <span className="mt-2 block font-medium leading-6 text-foreground">
                        {section.title}
                      </span>
                    </span>

                    <ChevronRight
                      className="mt-1 size-5 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                  </button>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default BrowseSectionList