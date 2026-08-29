import { useEffect, useState } from "react"
import {
  CircleAlert,
  ExternalLink,
  FileText,
} from "lucide-react"

import { getBrowseSection } from "@/api/browse"
import { ApiError } from "@/api/client"

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { formatEffectiveDate } from "@/lib/utils"

function formatManualText(text) {
  if (!text) return ""

  return text
    // INZ source extraction can place inline section references on their own lines.
    .replace(
      /\s*\n\s*([A-Z]{1,3}\d+(?:\.\d+)*)\s*\n\s*/g,
      " $1 ",
    )
    // Remove spaces introduced before punctuation after joining references.
    .replace(/\s+([),.;:])/g, "$1")
    .replace(/\(\s+/g, "(")
}


/**
 * Loads and displays one complete indexed Operational Manual section.
 *
 * The backend reconstructs the section from its stored chunks before sending
 * it here. Chunk boundaries are a retrieval concern and are intentionally not
 * exposed to the reader.
 */
function BrowseSectionDetail({
  sectionCode,
  onInvalidSection,
}) {
  const [section, setSection] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const controller = new AbortController()

    /**
     * Reload the section whenever the section code in the URL changes.
     *
     * Cancelling the previous request prevents stale section data from being
     * rendered if the user navigates quickly between sections.
     */
    async function loadSection() {
      setIsLoading(true)
      setError(null)
      setSection(null)

      try {
        const data = await getBrowseSection(
          sectionCode,
          controller.signal,
        )

        setSection(data)
    } catch (requestError) {
        if (requestError.name === "AbortError") {
            return
        }

        /*
        * A 404 means the section code in the URL does not exist.
        *
        * This is navigation validation rather than an application failure, so
        * return the user to the valid branch level instead of showing an error.
        */
        if (
            requestError instanceof ApiError &&
            requestError.status === 404
        ) {
            onInvalidSection()
            return
        }

        console.error(
            `Waypoint /browse/sections/${sectionCode} request failed:`,
            requestError,
        )

        setError(
            "Waypoint could not load this Operational Manual section. Please try again.",
        )
    } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    loadSection()

    return () => {
      controller.abort()
    }
  }, [sectionCode])

  if (isLoading) {
    return (
      <section aria-label="Loading Operational Manual section">
        <Card>
          <CardHeader className="space-y-3">
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-7 w-3/4" />
            <Skeleton className="h-4 w-36" />
          </CardHeader>

          <CardContent className="space-y-3">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-11/12" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-4/5" />
          </CardContent>
        </Card>
      </section>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <CircleAlert className="size-4" />

        <AlertTitle>Section could not be loaded</AlertTitle>

        <AlertDescription>
          {error}
        </AlertDescription>
      </Alert>
    )
  }

  if (!section) {
    return null
  }

  const effectiveDate = formatEffectiveDate(section.effective_date)

  return (
    <section aria-labelledby="section-detail-heading">
      <Card>
        <CardHeader className="border-b bg-muted/20">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              {section.section_code}
            </Badge>

            {effectiveDate && (
              <span className="text-xs text-muted-foreground">
                Effective {effectiveDate}
              </span>
            )}
          </div>

          <CardTitle
            id="section-detail-heading"
            className="mt-2 text-xl leading-7 text-waypoint-navy sm:text-2xl"
          >
            {section.title}
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-6 p-5 sm:p-6">
          <div>
            <div className="mb-3 flex items-center gap-2">
              <FileText
                className="size-4 text-waypoint-blue"
                strokeWidth={1.8}
                aria-hidden="true"
              />

              <h2 className="text-sm font-semibold text-foreground">
                Indexed Operational Manual text
              </h2>
            </div>

            {/*
              The backend returns plain text, not trusted HTML.

              whitespace-pre-wrap preserves paragraph and line breaks while
              React still escapes the text safely. We deliberately avoid
              dangerouslySetInnerHTML here.
            */}
            <div className="whitespace-pre-wrap text-[0.95rem] leading-7 text-foreground/90">
              {section.text}
            </div>
          </div>

          <div className="border-t pt-5">
            <p className="text-sm leading-6 text-muted-foreground">
              Immigration New Zealand is the authoritative publisher of this
              Operational Manual content. Check the original source for the
              current instruction.
            </p>

            <a
              href={section.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex min-h-11 items-center gap-2 font-medium text-waypoint-blue hover:underline"
            >
              View original INZ source

              <ExternalLink
                className="size-4"
                strokeWidth={1.8}
                aria-hidden="true"
              />
            </a>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}

export default BrowseSectionDetail