import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
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

function beautifyManualText(text) {
  if (!text) return ""

  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  const paragraphs = []
  let current = []

  const flush = () => {
    if (current.length === 0) return

    const paragraph = current
      .join(" ")
      // Remove spaces introduced before punctuation.
      .replace(/\s+([),.;:!?])/g, "$1")
      .replace(/\(\s+/g, "(")
      .trim()

    if (paragraph) {
      paragraphs.push(paragraph)
    }

    current = []
  }

  for (const line of lines) {
    current.push(line)

    // A colon normally introduces a list or explanatory block.
    if (line.endsWith(":")) {
      flush()
      continue
    }

    // Finish a paragraph when the extracted text reaches a full sentence.
    if (line === "." || /[.!?]$/.test(line)) {
      flush()
    }
  }

  flush()

  return paragraphs.join("\n\n")
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
  // The useQuery hook from React Query is used to fetch the section data from the backend.
  const {
    data: section,
    isPending: isLoading,
    error: sectionError,
  } = useQuery({
    queryKey: [
      "browse",
      "section",
      sectionCode,
    ],
    // The backend reconstructs the section from its stored chunks before sending
    queryFn: ({ signal }) =>
      getBrowseSection(sectionCode, signal),
    // The section content is not expected to change often, so a 5-minute cache is reasonable.
    staleTime: 5 * 60 * 1000,

    // An invalid section will never succeed on retry.
    // Other GET failures get one inexpensive retry.
    retry: (failureCount, error) => {
      if (
        error instanceof ApiError &&
        error.status === 404
      ) {
        return false
      }

      return failureCount < 1
    },
  })  
  // The onInvalidSection callback is called when the backend returns a 404 for
  // the requested section. This is a signal to the parent page that the user
  // has navigated to a non-existent section, so it can redirect them to a
  // valid location.
  useEffect(() => {
    if (
      sectionError instanceof ApiError &&
      sectionError.status === 404
    ) {
      onInvalidSection()
    }
  }, [sectionError, onInvalidSection])
  // The error message is only shown for non-404 errors, because a 404 is handled 
  // by the parent page redirecting the user to a valid section.
  const error =
    sectionError &&
    !(
      sectionError instanceof ApiError &&
      sectionError.status === 404
    )
      ? "Waypoint could not load this Operational Manual section. Please try again."
      : null

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
              {beautifyManualText(section.text)}
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