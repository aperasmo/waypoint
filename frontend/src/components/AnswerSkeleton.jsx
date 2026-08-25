import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

/**
 * Displays the loading placeholder for a Waypoint answer.
 *
 * The skeleton roughly mirrors AnswerPanel so the page does not jump
 * dramatically when the completed response replaces the loading state.
 */
function AnswerSkeleton() {
  return (
    <Card className="mt-8 overflow-hidden" aria-busy="true">
      <CardHeader className="space-y-3 border-b bg-muted/25">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-5 w-3/4" />
      </CardHeader>

      <CardContent className="space-y-6 p-5 sm:p-6">
        {/* Evidence status placeholder */}
        <div className="flex gap-3 rounded-xl border p-4">
          <Skeleton className="size-9 shrink-0 rounded-full" />

          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-52 max-w-full" />
            <Skeleton className="h-3 w-full max-w-md" />
          </div>
        </div>

        {/* Main answer placeholder */}
        <div className="space-y-3">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </div>

        {/* Citation placeholder */}
        <div className="space-y-3">
          <Skeleton className="h-4 w-24" />

          <div className="rounded-xl border p-4">
            <div className="flex items-center gap-3">
              <Skeleton className="size-9 rounded-full" />

              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-28" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default AnswerSkeleton