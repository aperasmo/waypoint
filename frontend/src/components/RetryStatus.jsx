import { Loader2 } from "lucide-react"

import { Alert, AlertDescription } from "@/components/ui/alert"

/**
 * Shown while /ask is being retried after a transient capacity error.
 *
 * Uses role="status" rather than AskError's role="alert": this is a polite,
 * in-progress update (assistive tech announces it without interrupting),
 * not a failure demanding immediate attention.
 */
function RetryStatus({ message }) {
  if (!message) {
    return null
  }

  return (
    <Alert role="status" className="mt-8 bg-muted/40">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />

      <AlertDescription className="leading-6 text-muted-foreground">
        {message}
      </AlertDescription>
    </Alert>
  )
}

export default RetryStatus
