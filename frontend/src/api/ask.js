import { ApiError, fetchJson } from "@/api/client"

// Initial request + up to 2 retries. /ask calls OpenAI on every successful
// execution, so retries stay small and bounded rather than "keep trying
// until it works" - each extra attempt is an extra potential OpenAI cost.
const MAX_RETRIES = 2
const BASE_RETRY_DELAY_MS = 2000
const MAX_RETRY_DELAY_MS = 10000

// 429 is API Gateway/Lambda throttling - the canonical "try again shortly"
// signal. 502/503/504 are gateway/upstream failures that usually mean the
// Lambda couldn't be reached or start in time, not a broken request. 500 is
// deliberately excluded: it means our own backend raised an unhandled
// error, and retrying a broken request just repeats it (and its OpenAI
// call) for no benefit.
const RETRYABLE_STATUSES = new Set([429, 502, 503, 504])

const BUSY_MESSAGE =
  "Waypoint is receiving more requests than it can handle right now. Please wait a moment and try again."

/**
 * Thrown when /ask remained retryably busy through every retry attempt.
 *
 * Kept distinct from ApiError so the UI can show a calm, specific message
 * without inspecting status codes itself.
 */
export class BusyError extends Error {
  constructor(message = BUSY_MESSAGE) {
    super(message)
    this.name = "BusyError"
  }
}

function isRetryableStatus(status) {
  return RETRYABLE_STATUSES.has(status)
}

/**
 * Parses a Retry-After header per RFC 9110: either an integer number of
 * seconds or an HTTP-date. Returns null for anything else (missing,
 * malformed, negative) so the caller falls back to its own backoff instead
 * of trusting an unusable value.
 *
 * @param {string | null} value - Raw Retry-After header value.
 * @returns {number | null} Delay in milliseconds, or null.
 */
export function parseRetryAfterMs(value) {
  if (!value) {
    return null
  }

  if (/^\d+$/.test(value.trim())) {
    return Number(value) * 1000
  }

  const dateMs = Date.parse(value)
  if (Number.isNaN(dateMs)) {
    return null
  }

  return Math.max(0, dateMs - Date.now())
}

/**
 * Backoff for one retry attempt (1-indexed). Uses Retry-After when the
 * server supplied a usable one, otherwise exponential backoff from
 * BASE_RETRY_DELAY_MS. Small random jitter keeps many clients that were
 * throttled together from retrying in the same instant. A hard cap bounds
 * both a huge/malformed Retry-After value and the exponential growth, so a
 * bad header or a high attempt count can never freeze the UI for long.
 */
function computeBackoffMs(attempt, retryAfterMs) {
  const base = retryAfterMs ?? BASE_RETRY_DELAY_MS * 2 ** (attempt - 1)
  const jitter = Math.random() * 300
  return Math.min(base + jitter, MAX_RETRY_DELAY_MS)
}

/**
 * Waits `ms`, but resolves early - without triggering a retry - if `signal`
 * aborts, so a cancelled request never keeps the caller waiting on a stale
 * backoff.
 */
function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"))
      return
    }

    const timeoutId = setTimeout(resolve, ms)

    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timeoutId)
        reject(new DOMException("Aborted", "AbortError"))
      },
      { once: true },
    )
  })
}

/**
 * Sends a policy question to Waypoint's /ask endpoint, retrying a bounded
 * number of times when the failure looks like temporary backend capacity
 * saturation (API Gateway/Lambda throttling or gateway errors) rather than
 * a genuine request or application error.
 *
 * This module knows the /ask contract and its retry policy, while client.js
 * handles generic HTTP behaviour shared across the frontend.
 *
 * @param {string} question - The user's submitted immigration question.
 * @param {object} [options]
 * @param {AbortSignal} [options.signal] - Cancels the in-flight request or
 *   an in-progress backoff wait.
 * @param {(attempt: number, maxRetries: number) => void} [options.onRetry] -
 *   Called just before each retry's backoff wait, so the caller can show a
 *   "busy, retrying" status without owning the retry algorithm itself.
 * @returns {Promise<object>} The parsed /ask response.
 * @throws {BusyError} When every retry attempt still failed as busy.
 * @throws {ApiError} For non-retryable HTTP failures (e.g. 422).
 */
export async function askWaypoint(question, { signal, onRetry } = {}) {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await fetchJson("/ask", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          question,
        }),

        signal,
      })
    } catch (error) {
      const canRetry =
        error instanceof ApiError &&
        isRetryableStatus(error.status) &&
        attempt < MAX_RETRIES

      if (!canRetry) {
        if (error instanceof ApiError && isRetryableStatus(error.status)) {
          throw new BusyError()
        }
        throw error
      }

      onRetry?.(attempt + 1, MAX_RETRIES)

      const retryAfterMs = parseRetryAfterMs(error.retryAfter)
      await wait(computeBackoffMs(attempt + 1, retryAfterMs), signal)
    }
  }
}
