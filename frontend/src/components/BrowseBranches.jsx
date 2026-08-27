import { ChevronRight, Files } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

/**
 * Displays the browse branches belonging to one selected topic.
 *
 * Branch names and section counts come directly from /browse/categories.
 * This component only presents that backend data and reports selections
 * back to the parent Browse page.
 */
function BrowseBranches({
  group,
  selectedBranch,
  onBranchSelect,
}) {
  if (!group) {
    return null
  }

  return (
    <section
      className="mt-10"
      aria-labelledby="browse-branches-heading"
    >
      <p className="text-sm font-semibold text-waypoint-blue">
        {group.label}
      </p>

      <h2
        id="browse-branches-heading"
        className="mt-1 text-xl font-semibold text-foreground"
      >
        Choose an area
      </h2>

      <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
        Select an area to see the Operational Manual sections currently
        indexed by Waypoint.
      </p>

      <div className="mt-5 space-y-3">
        {group.branches.map((branch) => {
          const isSelected = branch.label === selectedBranch

          return (
            <Card
              key={branch.label}
              className={
                isSelected
                  ? "border-waypoint-blue ring-1 ring-waypoint-blue"
                  : "transition-colors hover:border-waypoint-blue/50"
              }
            >
              <CardContent className="p-0">
                <button
                  type="button"
                  onClick={() => onBranchSelect(branch.label)}
                  className="flex w-full items-center gap-4 p-4 text-left sm:p-5"
                  aria-pressed={isSelected}
                >
                  <span
                    className="flex size-9 shrink-0 items-center justify-center rounded-full bg-waypoint-info-soft text-waypoint-info"
                    aria-hidden="true"
                  >
                    <Files className="size-4" strokeWidth={1.8} />
                  </span>

                  <span className="min-w-0 flex-1">
                    <span className="font-medium text-foreground">
                      {branch.label}
                    </span>

                    <span className="mt-1 block text-sm text-muted-foreground">
                      {branch.section_count === 1
                        ? "1 indexed section"
                        : `${branch.section_count} indexed sections`}
                    </span>
                  </span>

                  <Badge
                    variant="secondary"
                    className="shrink-0"
                  >
                    {branch.section_count}
                  </Badge>

                  <ChevronRight
                    className="size-5 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                </button>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </section>
  )
}

export default BrowseBranches