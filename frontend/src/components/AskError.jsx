import { CircleAlert } from "lucide-react"

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert"

/**
 * Presents failures from the /ask request in user-friendly language.
 *
 * Technical errors should be logged separately. Users should receive a
 * useful recovery message rather than raw server or network details.
 */
function AskError({ message }) {
  if (!message) {
    return null
  }

  return (
    <Alert
      variant="destructive"
      className="mt-8"
      role="alert"
    >
      <CircleAlert className="size-4" />

      <AlertTitle>Waypoint could not complete this request</AlertTitle>

      <AlertDescription className="leading-6">
        {message}
      </AlertDescription>
    </Alert>
  )
}

export default AskError