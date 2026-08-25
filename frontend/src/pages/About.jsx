import {
  BookOpen,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  Info,
  ShieldCheck,
} from "lucide-react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

/**
 * Explains Waypoint's purpose, evidence model, and limitations.
 *
 * This page intentionally avoids corpus counts or coverage claims that are not
 * supplied by the backend. Its purpose is to explain how to interpret results.
 */
function About() {
  return (
    <section className="mx-auto max-w-3xl">
      <p className="mb-2 text-sm font-semibold text-waypoint-blue">
        About the project
      </p>

      <h1 className="text-3xl font-semibold tracking-tight text-waypoint-navy sm:text-4xl">
        About Waypoint
      </h1>

      <p className="mt-4 max-w-2xl leading-7 text-muted-foreground">
        Waypoint is an evidence-based research interface for exploring
        immigration instructions from the indexed Immigration New Zealand
        Operational Manual.
      </p>

      <div className="mt-8 space-y-5">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <span
                className="flex size-10 items-center justify-center rounded-full bg-waypoint-info-soft text-waypoint-info"
                aria-hidden="true"
              >
                <BookOpen className="size-5" strokeWidth={1.8} />
              </span>

              <CardTitle>How Waypoint works</CardTitle>
            </div>
          </CardHeader>

          <CardContent className="space-y-4 leading-7 text-muted-foreground">
            <p>
              When you ask a question, Waypoint searches its indexed copy of
              the publicly available Operational Manual for relevant
              immigration instructions.
            </p>

            <p>
              The answer is generated from the retrieved evidence and is
              accompanied by citations so you can inspect the supporting
              Operational Manual sections yourself.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <span
                className="flex size-10 items-center justify-center rounded-full bg-waypoint-success-soft text-waypoint-success"
                aria-hidden="true"
              >
                <CheckCircle2 className="size-5" strokeWidth={1.8} />
              </span>

              <CardTitle>Evidence states</CardTitle>
            </div>
          </CardHeader>

          <CardContent className="space-y-5">
            <div>
              <p className="font-medium text-foreground">
                Answered from the Operational Manual
              </p>

              <p className="mt-1 leading-6 text-muted-foreground">
                The indexed evidence is sufficient to support an answer.
              </p>
            </div>

            <div>
              <p className="font-medium text-foreground">
                The indexed Operational Manual does not contain enough
                information
              </p>

              <p className="mt-1 leading-6 text-muted-foreground">
                Waypoint does not have enough indexed evidence to support a
                complete answer.
              </p>
            </div>

            <div>
              <p className="font-medium text-foreground">
                Information outside the Operational Manual is required
              </p>

              <p className="mt-1 leading-6 text-muted-foreground">
                The authoritative answer depends on information maintained
                outside the indexed Operational Manual.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <span
                className="flex size-10 items-center justify-center rounded-full bg-waypoint-warning-soft text-waypoint-warning"
                aria-hidden="true"
              >
                <CircleAlert className="size-5" strokeWidth={1.8} />
              </span>

              <CardTitle>What Waypoint does not do</CardTitle>
            </div>
          </CardHeader>

          <CardContent>
            <ul className="space-y-3 text-sm leading-6 text-muted-foreground">
              <li className="flex gap-3">
                <span
                  className="mt-[0.65rem] size-1.5 shrink-0 rounded-full bg-waypoint-warning"
                  aria-hidden="true"
                />
                <span>Waypoint does not provide immigration advice.</span>
              </li>

              <li className="flex gap-3">
                <span
                  className="mt-[0.65rem] size-1.5 shrink-0 rounded-full bg-waypoint-warning"
                  aria-hidden="true"
                />
                <span>
                  It does not make visa eligibility or application decisions.
                </span>
              </li>

              <li className="flex gap-3">
                <span
                  className="mt-[0.65rem] size-1.5 shrink-0 rounded-full bg-waypoint-warning"
                  aria-hidden="true"
                />
                <span>
                  It should not be treated as a complete substitute for
                  Immigration New Zealand or a licensed immigration adviser.
                </span>
              </li>

              <li className="flex gap-3">
                <span
                  className="mt-[0.65rem] size-1.5 shrink-0 rounded-full bg-waypoint-warning"
                  aria-hidden="true"
                />
                <span>
                  Some authoritative information may be maintained outside the
                  Operational Manual.
                </span>
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card>
        <CardHeader>
            <CardTitle>Source and attribution</CardTitle>
        </CardHeader>

        <CardContent className="space-y-4 leading-7 text-muted-foreground">
            <p>
            Waypoint uses publicly available immigration instructions published by
            Immigration New Zealand in the Immigration New Zealand Operational Manual
            as its primary source material.
            </p>

            <p>
            Where Waypoint provides an answer from the Operational Manual, the
            supporting section code, title, effective date where available, and a
            link to the corresponding Immigration New Zealand source are provided so
            the original instruction can be checked directly.
            </p>

            <p>
            Immigration New Zealand remains the authoritative publisher of the
            Operational Manual. Waypoint is an independent research interface and is
            not affiliated with, endorsed by, or an official service of Immigration
            New Zealand.
            </p>
        </CardContent>
        </Card>


        <Alert>
          <ShieldCheck className="size-4" />

          <AlertDescription className="leading-6">
            Waypoint is an independent research project. It is not affiliated
            with, endorsed by, or an official service of Immigration New
            Zealand.
          </AlertDescription>
        </Alert>

        <div className="flex items-start gap-3 rounded-xl border bg-muted/30 p-4">
          <Info
            className="mt-0.5 size-5 shrink-0 text-waypoint-blue"
            strokeWidth={1.8}
            aria-hidden="true"
          />

          <div>
            <p className="font-medium text-foreground">
              Check the source
            </p>

            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Waypoint citations include links to the source immigration
              instructions. Use those links to inspect the underlying evidence
              and confirm that it remains current.
            </p>
          </div>

          {/* <ExternalLink
            className="ml-auto size-4 shrink-0 text-muted-foreground"
            aria-hidden="true"
          /> */}
        </div>
      </div>
    </section>
  )
}

export default About