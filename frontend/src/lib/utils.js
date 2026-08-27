import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}


/**
 * Formats an ISO calendar date for the New Zealand UI.
 *
 * The backend returns dates such as "2026-04-20". Appending midnight keeps
 * the value anchored to that calendar date instead of allowing timezone
 * conversion to shift it to the previous day.
 *
 * @param {string | null | undefined} value - ISO date in YYYY-MM-DD format.
 * @returns {string | null} Human-readable date such as "20 Apr 2026".
 */
export function formatEffectiveDate(value) {
  if (!value) {
    return null
  }

  const date = new Date(`${value}T00:00:00`)

  // Preserve the original value if the backend ever returns an unexpected
  // date format rather than hiding the information completely.
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat("en-NZ", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date)
}