import { ShieldCheck } from "lucide-react"

import CitationList from "@/components/CitationList"
import EvidenceStatus from "@/components/EvidenceStatus"
import FeedbackReport from "@/components/FeedbackReport"
import MissingInformation from "@/components/MissingInformation"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

/**
 * Displays one complete Waypoint response.
 *
 * This component does not decide whether evidence is sufficient.
 * It only renders the decision already returned by the backend.
 */
function AnswerPanel({
  question,
  interpretedAs,
  answer,
  evidenceStatus,
  citations = [],
  missingInformation = [],
  disclaimer,
}) {
  return (
    <Card className="mt-8 overflow-hidden">
      <CardHeader className="border-b bg-muted/25">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Your question
        </p>

        <CardTitle className="text-base font-medium leading-6">
          {question}
        </CardTitle>

        {/*
            Show the backend interpretation only when it differs from the original
            question. This makes query expansion transparent without adding noise to
            every response.
        */}
        {interpretedAs &&
            interpretedAs.trim().toLowerCase() !== question.trim().toLowerCase() && (
            <div className="mt-3 rounded-lg bg-muted/60 px-3 py-2">
                <p className="text-xs font-semibold text-muted-foreground">
                Interpreted as
                </p>

                <p className="mt-1 text-sm leading-6 text-foreground/80">
                {interpretedAs}
                </p>
            </div>
            )}

      </CardHeader>

      <CardContent className="space-y-6 p-5 sm:p-6">
        {/*
          evidenceStatus comes directly from the API contract.
          EvidenceStatus translates the backend value into user-facing wording.
        */}
        <EvidenceStatus status={evidenceStatus} />

        <section aria-labelledby="answer-heading">
          <h2
            id="answer-heading"
            className="text-sm font-semibold text-foreground"
          >
            Answer
          </h2>

          {/*
            whitespace-pre-line preserves intentional line breaks from the
            backend answer without requiring HTML rendering.
          */}
          <p className="mt-3 whitespace-pre-line text-[0.95rem] leading-7 text-foreground/90">
            {answer}
          </p>
        </section>

        {/*
          CitationList and MissingInformation already return null when their
          arrays are empty, so AnswerPanel does not need duplicate conditions.
        */}
        <CitationList citations={citations} />

        <MissingInformation items={missingInformation} />

        {/*
          The disclaimer is shown only when one is supplied.
          This keeps the component compatible with future response types.
        */}
        {disclaimer && (
          <Alert className="bg-muted/40">
            <ShieldCheck className="size-4" />

            <AlertDescription className="leading-6 text-muted-foreground">
              {disclaimer}
            </AlertDescription>
          </Alert>
        )}

        {/*
          Anonymous review feedback on this specific response. Sends a
          snapshot of the answer/evidence status/citations already on
          screen, not the (by-then-cleared) question textarea.
        */}
        <FeedbackReport
          question={question}
          answer={answer}
          evidenceStatus={evidenceStatus}
          citedSections={citations.map((citation) => citation.section_code)}
        />
      </CardContent>
    </Card>
  )
}

export default AnswerPanel