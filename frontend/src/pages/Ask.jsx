import { useState } from "react"

import { askWaypoint } from "@/api/ask"
import AnswerPanel from "@/components/AnswerPanel"
import AnswerSkeleton from "@/components/AnswerSkeleton"
import AskError from "@/components/AskError"
import QuestionForm from "@/components/QuestionForm"

function Ask() {
  // Stores the text currently being edited in the question field.
  const [question, setQuestion] = useState("")

  // Stores the most recent successful response returned by POST /ask.
  const [response, setResponse] = useState(null)

  // Tracks whether an /ask request is currently in progress.
  const [isLoading, setIsLoading] = useState(false)

  // Stores a user-facing error message. Null means no error is active.
  const [error, setError] = useState(null)

  /**
   * Submits the current question to the Waypoint backend.
   *
   * The request lifecycle is:
   * clear previous state -> show loading -> request /ask ->
   * store success or error -> stop loading.
   */
  async function handleSubmit() {
    const submittedQuestion = question.trim()

    // QuestionForm already prevents blank submission, but this second guard
    // keeps the page handler safe if it is called from somewhere else later.
    if (!submittedQuestion) {
      return
    }

    setIsLoading(true)
    setError(null)
    setResponse(null)

    try {
      const data = await askWaypoint(submittedQuestion)

      setResponse(data)
      setQuestion("")
    } catch (requestError) {
      /**
       * Keep technical details available to developers while presenting a
       * stable, useful message to the user.
       */
      console.error("Waypoint /ask request failed:", requestError)

      setError(
        "Waypoint could not reach the policy service. Please try again.",
      )
    } finally {
      // finally executes whether the request succeeds or fails.
      setIsLoading(false)
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

      {isLoading && <AnswerSkeleton />}

      {!isLoading && response && (
        <AnswerPanel
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