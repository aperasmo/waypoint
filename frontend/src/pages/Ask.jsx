import { useEffect, useRef, useState } from "react"

import { askWaypoint, BusyError } from "@/api/ask"
import AnswerPanel from "@/components/AnswerPanel"
import AnswerSkeleton from "@/components/AnswerSkeleton"
import AskError from "@/components/AskError"
import QuestionForm from "@/components/QuestionForm"
import RetryStatus from "@/components/RetryStatus"

import { useMutation } from "@tanstack/react-query" // React Query is used to manage the state of the /ask request and its retries.

function Ask() {
  // Stores the most recent successful response returned by POST /ask.
  //const [response, setResponse] = useState(null) 

  // Tracks whether an /ask request (including any retries) is in progress.
  //const [isLoading, setIsLoading] = useState(false)

  // Stores a user-facing error message. Null means no error is active.
  //const [error, setError] = useState(null)

  // Stores the text currently being edited in the question field.
  const [question, setQuestion] = useState("")

  // Bumped on every new response so AnswerPanel (and the feedback form
  // nested inside it) remounts instead of carrying over state from the
  // previous answer.
  const [responseId, setResponseId] = useState(0)

  // User-facing "busy, retrying" status shown while askWaypoint retries
  // after a transient capacity error. Null means no retry is in progress.
  const [retryStatus, setRetryStatus] = useState(null)

  // Aborts the in-flight request/backoff on unmount; also guards against
  // setting state after that point, since askWaypoint's retry loop can
  // still be mid-wait when the user navigates away.
  const mountedRef = useRef(true)
  const abortControllerRef = useRef(null)
  // React Query's useMutation hook is used to manage the state of the /ask request and its retries. 
  // It provides a mutation function that calls askWaypoint with the current question, an abort signal, and a retry callback. The retry option is set to false because askWaypoint already implements its own retry logic.
  const askMutation = useMutation({
    mutationFn: ({ question, signal, onRetry }) =>
      askWaypoint(question, {
        signal,
        onRetry,
      }),

    // askWaypoint already owns Waypoint's bounded retry policy.
    // A second retry layer here could trigger extra LLM calls.
    retry: false,
  })

  // The mountedRef and abortControllerRef are used to manage the component's lifecycle and prevent state updates after unmounting. 
  // The useEffect hook sets mountedRef to true on mount and cleans up by setting it to false and aborting any in-flight requests on unmount.
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
    // This is a defensive guard against future changes that might call handleSubmit
    // from somewhere else, or if the user double-clicks the submit button.
    // The askMutation.isPending flag is provided by React Query and indicates whether the mutation is currently in progress.
    if (askMutation.isPending) {
      return
    }

    const controller = new AbortController()
    abortControllerRef.current = controller
    // Reset the mutation state and clear any previous error or retry status before starting a new request.
    askMutation.reset()
    setRetryStatus(null)
    // Clear the previous response and error state to prepare for a new request.
    try {
      const data = await askMutation.mutateAsync({
        question: submittedQuestion,
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

      // setError(
      //   requestError instanceof BusyError
      //     ? requestError.message
      //     : "Waypoint could not reach the policy service. Please try again.",
      // )
    } finally {
      if (mountedRef.current) {
        setRetryStatus(null)
      }
    }
  }
  // The response, isLoading, and error variables are derived from the askMutation state provided by React Query.
  const response = askMutation.data
  const isLoading = askMutation.isPending

  const error =
    askMutation.error instanceof BusyError
      ? askMutation.error.message
      : askMutation.error
        ? "Waypoint could not reach the policy service. Please try again."
        : null

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