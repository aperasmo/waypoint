import { Flag } from "lucide-react"
import { useState } from "react"

import { submitFeedback } from "@/api/feedback"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

const FEEDBACK_TYPES = [
  { value: "not_answered", label: "My question wasn't answered" },
  { value: "outside_coverage", label: "This seems outside Waypoint's coverage" },
  { value: "incorrect_answer", label: "The answer seems incorrect" },
  { value: "irrelevant_sources", label: "The sources don't seem relevant" },
  {
    value: "external_information_needed",
    label: "I need information that isn't in the Manual",
  },
  { value: "other", label: "Other" },
]

// These two evidence statuses mean Waypoint already knows the answer was
// incomplete, so the collapsed prompt can say so directly instead of asking
// "was something wrong" about an answer that already flagged its own gap.
const GAP_STATUSES = new Set(["corpus_gap", "external_source_required"])

/**
 * Lets a reader flag a problem with the response currently on screen.
 *
 * Submits a snapshot of the question, answer, evidence status, and cited
 * sections the user actually saw. The Ask textarea clears itself after a
 * successful request, so this component cannot rely on it and instead takes
 * that context as props from the rendered response.
 *
 * Callers should remount this component (e.g. via a `key` on the parent
 * answer panel) when a new response replaces the old one, so open/submitted
 * state and any typed comment never leak from one answer to the next.
 */
function FeedbackReport({ question, answer, evidenceStatus, citedSections = [] }) {
  const [isOpen, setIsOpen] = useState(false)
  const [feedbackType, setFeedbackType] = useState("")
  const [comment, setComment] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [error, setError] = useState(null)

  const isGap = GAP_STATUSES.has(evidenceStatus)

  function handleCancel() {
    setIsOpen(false)
    setFeedbackType("")
    setComment("")
    setError(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()

    if (!feedbackType || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      await submitFeedback({
        question,
        feedback_type: feedbackType,
        comment: comment.trim() || null,
        evidence_status: evidenceStatus ?? null,
        answer: answer ?? null,
        cited_sections: citedSections,
      })

      setIsSubmitted(true)
    } catch (submitError) {
      console.error("Waypoint /feedback request failed:", submitError)

      // feedbackType and comment are intentionally left in place so the
      // user can retry without re-entering anything.
      setError("Could not send your feedback. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  if (isSubmitted) {
    return (
      <div
        role="status"
        className="rounded-xl border bg-muted/25 px-4 py-3 text-sm text-muted-foreground"
      >
        Thanks. Your feedback has been recorded.
      </div>
    )
  }

  if (!isOpen) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-muted/10 px-4 py-3">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Flag className="size-4 shrink-0" aria-hidden="true" />
          {isGap
            ? "Waypoint could not fully answer this from the indexed Manual."
            : "Was something wrong with this answer?"}
        </p>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setIsOpen(true)}
        >
          {isGap ? "Tell us what you were looking for" : "Report an issue"}
        </Button>
      </div>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border bg-card p-4"
      aria-label="Report an issue with this answer"
    >
      <fieldset>
        <legend className="text-sm font-semibold text-foreground">
          What was the issue?
        </legend>

        <div className="mt-3 space-y-2">
          {FEEDBACK_TYPES.map((option) => (
            <label
              key={option.value}
              className="flex min-h-6 cursor-pointer items-center gap-2 text-sm text-foreground/90"
            >
              <input
                type="radio"
                name="feedback-type"
                value={option.value}
                checked={feedbackType === option.value}
                onChange={() => setFeedbackType(option.value)}
                className="size-4 accent-waypoint-blue"
              />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="mt-4">
        <label
          htmlFor="feedback-comment"
          className="block text-sm font-medium text-foreground"
        >
          Optional comment
        </label>

        <Textarea
          id="feedback-comment"
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          placeholder="Tell us what you expected or what was missing."
          rows={3}
          className="mt-2"
        />

        <p className="mt-2 text-xs text-muted-foreground">
          Please do not include passport numbers, application numbers, or
          other sensitive personal information.
        </p>
      </div>

      {error && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {error}
        </p>
      )}

      <div className="mt-4 flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleCancel}
          disabled={isSubmitting}
        >
          Cancel
        </Button>

        <Button type="submit" size="sm" disabled={!feedbackType || isSubmitting}>
          {isSubmitting ? "Sending..." : "Send feedback"}
        </Button>
      </div>
    </form>
  )
}

export default FeedbackReport
