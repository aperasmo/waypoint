import { useEffect, useRef, useState } from "react"

import { askWaypoint, BusyError } from "@/api/ask"
import AnswerPanel from "@/components/AnswerPanel"
import AnswerSkeleton from "@/components/AnswerSkeleton"
import AskError from "@/components/AskError"
import QuestionForm from "@/components/QuestionForm"
import RetryStatus from "@/components/RetryStatus"

function Ask() {
  // Stores the text currently being edited in the question field.
  const [question, setQuestion] = useState("")

  // Stores the most recent successful response returned by POST /ask.
  const [response, setResponse] = useState(null)

  // Bumped on every new response so AnswerPanel (and the feedback form
  // nested inside it) remounts instead of carrying over state from the
  // previous answer.
  const [responseId, setResponseId] = useState(0)

  // Tracks whether an /ask request (including any retries) is in progress.
  const [isLoading, setIsLoading] = useState(false)

  // Stores a user-facing error message. Null means no error is active.
  const [error, setError] = useState(null)

  // User-facing "busy, retrying" status shown while askWaypoint retries
  // after a transient capacity error. Null means no retry is in progress.
  const [retryStatus, setRetryStatus] = useState(null)

  // Aborts the in-flight request/backoff on unmount; also guards against
  // setting state after that point, since askWaypoint's retry loop can
  // still be mid-wait when the user navigates away.
  const mountedRef = useRef(true)
  const abortControllerRef = useRef(null)

  useEffect(() => {
    mountedRef.current = true

    return () => {
      mountedRef.current = false
      abortControllerRef.current?.abort()
    }
  }, [])

  /**
   * Submits the current question to the Waypoint backend.
   *
   * The request lifecycle is:
   * clear previous state -> show loading -> request /ask (retrying
   * internally if the backend is temporarily busy) -> store success or
   * error -> stop loading.
   */
  async function handleSubmit() {
    const submittedQuestion = question.trim()

    // QuestionForm already prevents blank submission, but this second guard
    // keeps the page handler safe if it is called from somewhere else later.
    if (!submittedQuestion) {
      return
    }

    // isLoading already disables QuestionForm's submit button for the full
    // duration of a request-and-retry sequence, but this stops a second
    // submission (and a second OpenAI call) if handleSubmit is ever invoked
    // again while one is still in flight.
    if (isLoading) {
      return
    }

    const controller = new AbortController()
    abortControllerRef.current = controller

    setIsLoading(true)
    setError(null)
    setResponse(null)
    setRetryStatus(null)

    try {
      const data = await askWaypoint(submittedQuestion, {
        signal: controller.signal,

        onRetry: (attempt) => {
          if (!mountedRef.current) {
            return
          }

          setRetryStatus(
            attempt === 1
              ? "Waypoint is busy right now. Your question will be retried shortly."
              : "Waypoint is still busy. Retrying your question...",
          )
        },
      })

      if (!mountedRef.current) {
        return
      }

      setResponse(data)
      setResponseId((id) => id + 1)
      setQuestion("")
    } catch (requestError) {
      if (requestError.name === "AbortError" || !mountedRef.current) {
        return
      }

      /**
       * Keep technical details available to developers while presenting a
       * stable, useful message to the user. BusyError's message is already
       * user-safe (set by askWaypoint), so it is shown as-is.
       */
      console.error("Waypoint /ask request failed:", requestError)

      setError(
        requestError instanceof BusyError
          ? requestError.message
          : "Waypoint could not reach the policy service. Please try again.",
      )
    } finally {
      if (mountedRef.current) {
        setIsLoading(false)
        setRetryStatus(null)
      }
    }
  }

  return (
    <section className="mx-auto max-w-3xl">
      <p className="mb-2 text-sm font-semibold text-waypoint-blue">
        Operational Manual research
      </p>

      <h1 className="text-3xl font-semibold tracking-tight text-waypoint-navy sm:text-4xl">
        Ask Waypoint
      </h1>

      <p className="mt-4 max-w-2xl leading-7 text-muted-foreground">
        Ask an immigration policy question. Waypoint retrieves relevant
        evidence from the indexed Immigration New Zealand Operational Manual.
      </p>

      <QuestionForm
        question={question}
        onQuestionChange={setQuestion}
        onSubmit={handleSubmit}
        isLoading={isLoading}
      />

      <AskError message={error} />

      <RetryStatus message={retryStatus} />

      {isLoading && <AnswerSkeleton />}

      {!isLoading && response && (
        <AnswerPanel
          key={responseId}
          question={response.question}
          interpretedAs={response.interpreted_as}
          answer={response.answer}
          evidenceStatus={response.evidence_status}
          citations={response.citations}
          missingInformation={response.missing_information}
          disclaimer={response.disclaimer}
        />
      )}
    </section>
  )
}

export default Ask