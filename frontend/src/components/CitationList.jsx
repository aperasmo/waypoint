import { ExternalLink, FileText } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { formatEffectiveDate } from "@/lib/utils"


function CitationList({ citations = [] }) {
  if (citations.length === 0) {
    return null
  }

  return (
    <section aria-labelledby="sources-heading">
      <div className="flex items-center justify-between gap-4">
        <h2
          id="sources-heading"
          className="text-sm font-semibold text-foreground"
        >
          Sources ({citations.length})
        </h2>
      </div>

      <div className="mt-3 overflow-hidden rounded-xl border bg-card">
        {citations.map((citation, index) => {
          const effectiveDate = formatEffectiveDate(citation.effective_date)

          return (
            <div key={`${citation.section_code}-${index}`}>
              {index > 0 && <Separator />}

              <a
                href={citation.source_url}
                target="_blank"
                rel="noreferrer"
                className="group flex items-start gap-3 p-4 transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
              >
                <span
                  className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-waypoint-blue-soft text-waypoint-blue"
                  aria-hidden="true"
                >
                  <FileText className="size-4" strokeWidth={1.8} />
                </span>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">
                      {citation.section_code}
                    </Badge>

                    {effectiveDate && (
                      <span className="text-xs text-muted-foreground">
                        Effective {effectiveDate}
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-sm font-medium leading-6 text-foreground">
                    {citation.title}
                  </p>
                </div>

                <ExternalLink
                  className="mt-1 size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-waypoint-blue"
                  strokeWidth={1.8}
                  aria-hidden="true"
                />
              </a>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default CitationList