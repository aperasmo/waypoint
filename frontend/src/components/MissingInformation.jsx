import { CircleHelp } from "lucide-react"

function MissingInformation({ items = [] }) {
  if (items.length === 0) {
    return null
  }

  return (
    <section
      className="rounded-xl border bg-card p-4"
      aria-labelledby="missing-information-heading"
    >
      <div className="flex items-start gap-3">
        <span
          className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
          aria-hidden="true"
        >
          <CircleHelp className="size-5" strokeWidth={1.8} />
        </span>

        <div className="min-w-0 flex-1">
          <h2
            id="missing-information-heading"
            className="font-semibold text-foreground"
          >
            Information needed from you
          </h2>

          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            These details may be needed before a more specific assessment can
            be made.
          </p>

          <ul className="mt-3 space-y-2">
            {items.map((item, index) => (
              <li
                key={`${item}-${index}`}
                className="flex gap-2 text-sm leading-6 text-foreground/85"
              >
                <span
                  className="mt-[0.65rem] size-1.5 shrink-0 rounded-full bg-waypoint-blue"
                  aria-hidden="true"
                />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

export default MissingInformation