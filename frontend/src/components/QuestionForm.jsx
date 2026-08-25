import { Send } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

function QuestionForm({
  question,
  onQuestionChange,
  onSubmit,
  isLoading = false,
}) {
  const canSubmit = question.trim().length > 0 && !isLoading

  function handleSubmit(event) {
    event.preventDefault()

    if (!canSubmit) {
      return
    }

    onSubmit()
  }

  return (
    <form onSubmit={handleSubmit} className="mt-8">
      <label
        htmlFor="waypoint-question"
        className="mb-2 block text-sm font-semibold text-foreground"
      >
        Your question
      </label>

      <div className="rounded-2xl border bg-card p-2 shadow-sm transition-shadow focus-within:shadow-md">
        <Textarea
          id="waypoint-question"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          placeholder="Ask about an immigration instruction..."
          disabled={isLoading}
          rows={4}
          className="min-h-28 resize-none border-0 bg-transparent px-3 py-3 text-base shadow-none focus-visible:ring-0"
        />

        <div className="flex items-center justify-between gap-3 border-t px-2 pt-2">
          <p className="hidden text-xs text-muted-foreground sm:block">
            Waypoint answers from indexed Operational Manual evidence.
          </p>

          <Button
            type="submit"
            disabled={!canSubmit}
            className="ml-auto min-h-10 gap-2 px-4"
          >
            <span>{isLoading ? "Researching..." : "Ask Waypoint"}</span>
            <Send data-icon="inline-end" />
          </Button>
        </div>
      </div>
    </form>
  )
}

export default QuestionForm