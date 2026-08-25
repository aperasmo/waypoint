import {
  CheckCircle2,
  CircleAlert,
  ExternalLink,
} from "lucide-react"

const statusConfig = {
  sufficient: {
    label: "Answered from the Operational Manual",
    description:
      "The indexed Operational Manual contains sufficient evidence to answer this question.",
    icon: CheckCircle2,
    containerClass:
      "border-waypoint-success/25 bg-waypoint-success-soft",
    iconClass: "bg-waypoint-success text-white",
    textClass: "text-waypoint-success",
  },

  corpus_gap: {
    label:
      "The indexed Operational Manual does not contain enough information",
    description:
      "The available indexed evidence is not sufficient to support a complete answer.",
    icon: CircleAlert,
    containerClass:
      "border-waypoint-warning/25 bg-waypoint-warning-soft",
    iconClass: "bg-waypoint-warning text-white",
    textClass: "text-waypoint-warning",
  },

  external_source_required: {
    label: "Information outside the Operational Manual is required",
    description:
      "The authoritative information for this question is maintained outside the indexed Operational Manual.",
    icon: ExternalLink,
    containerClass:
      "border-waypoint-info/25 bg-waypoint-info-soft",
    iconClass: "bg-waypoint-info text-white",
    textClass: "text-waypoint-info",
  },
}

function EvidenceStatus({ status }) {
  const config = statusConfig[status]

  if (!config) {
    return null
  }

  const Icon = config.icon

  return (
    <div
      className={[
        "flex gap-3 rounded-xl border p-4",
        config.containerClass,
      ].join(" ")}
    >
      <span
        className={[
          "flex size-9 shrink-0 items-center justify-center rounded-full",
          config.iconClass,
        ].join(" ")}
        aria-hidden="true"
      >
        <Icon className="size-5" strokeWidth={2} />
      </span>

      <div>
        <p
          className={[
            "font-semibold leading-6",
            config.textClass,
          ].join(" ")}
        >
          {config.label}
        </p>

        <p className="mt-1 text-sm leading-6 text-foreground/75">
          {config.description}
        </p>
      </div>
    </div>
  )
}

export default EvidenceStatus