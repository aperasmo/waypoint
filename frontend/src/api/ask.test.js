import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { askWaypoint, BusyError, parseRetryAfterMs } from "@/api/ask"

/**
 * Builds a fetch Response stand-in. askWaypoint/client.js only touch
 * `ok`, `status`, `statusText`, `headers.get`, and `json()`.
 */
function jsonResponse(status, body, headers = {}) {
  const headerMap = new Map(Object.entries(headers))

  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: `Status ${status}`,
    headers: { get: (name) => headerMap.get(name) ?? null },
    json: async () => body,
  }
}

describe("askWaypoint retry policy", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal("fetch", vi.fn())
    // computeBackoffMs adds up to 300ms of jitter; pinning Math.random keeps
    // the exact backoff value assertions deterministic.
    vi.spyOn(Math, "random").mockReturnValue(0)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("does not retry a 200 response", async () => {
    fetch.mockResolvedValueOnce(jsonResponse(200, { answer: "ok" }))

    const result = await askWaypoint("Can I work?")

    expect(result).toEqual({ answer: "ok" })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it("does not retry a 422 response", async () => {
    fetch.mockResolvedValueOnce(jsonResponse(422, { detail: "bad input" }))

    const promise = askWaypoint("")
    await expect(promise).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
    })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it("retries once on 429 then succeeds", async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(429, {}))
      .mockResolvedValueOnce(jsonResponse(200, { answer: "ok" }))

    const onRetry = vi.fn()
    const promise = askWaypoint("Can I work?", { onRetry })

    await vi.runAllTimersAsync()
    const result = await promise

    expect(result).toEqual({ answer: "ok" })
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(onRetry).toHaveBeenCalledWith(1, 2)
  })

  it("stops after the configured maximum and surfaces a BusyError", async () => {
    fetch.mockResolvedValue(jsonResponse(503, {}))

    const onRetry = vi.fn()
    const promise = askWaypoint("Can I work?", { onRetry })
    // Prevent an unhandled-rejection warning while timers are still
    // advancing below; the real assertion happens after via `promise`.
    promise.catch(() => {})

    await vi.runAllTimersAsync()

    await expect(promise).rejects.toBeInstanceOf(BusyError)
    await expect(promise).rejects.toMatchObject({
      message: expect.stringContaining("receiving more requests"),
    })

    // Initial attempt + 2 retries = 3 calls total; never an unbounded loop.
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(onRetry).toHaveBeenCalledTimes(2)
  })

  it("uses a valid Retry-After header instead of the default backoff", async () => {
    fetch
      .mockResolvedValueOnce(jsonResponse(429, {}, { "Retry-After": "1" }))
      .mockResolvedValueOnce(jsonResponse(200, { answer: "ok" }))

    const promise = askWaypoint("Can I work?")

    // Advancing by exactly the Retry-After value (1s) should be enough to
    // resolve the retry; the default backoff would need 2s.
    await vi.advanceTimersByTimeAsync(1000)
    const result = await promise

    expect(result).toEqual({ answer: "ok" })
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it("falls back to default backoff when Retry-After is malformed", async () => {
    fetch
      .mockResolvedValueOnce(
        jsonResponse(429, {}, { "Retry-After": "not-a-real-value" }),
      )
      .mockResolvedValueOnce(jsonResponse(200, { answer: "ok" }))

    const promise = askWaypoint("Can I work?")

    await vi.advanceTimersByTimeAsync(2000)
    const result = await promise

    expect(result).toEqual({ answer: "ok" })
  })

  it("is abortable during the backoff wait and never issues a second fetch", async () => {
    fetch.mockResolvedValueOnce(jsonResponse(429, {}))

    const controller = new AbortController()
    const promise = askWaypoint("Can I work?", { signal: controller.signal })
    promise.catch(() => {})

    controller.abort()
    await vi.runAllTimersAsync()

    await expect(promise).rejects.toMatchObject({ name: "AbortError" })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})

describe("parseRetryAfterMs", () => {
  it("parses integer seconds", () => {
    expect(parseRetryAfterMs("2")).toBe(2000)
  })

  it("returns null for missing or malformed values", () => {
    expect(parseRetryAfterMs(null)).toBeNull()
    expect(parseRetryAfterMs("")).toBeNull()
    expect(parseRetryAfterMs("not-a-date")).toBeNull()
  })

  it("parses an HTTP-date relative to now", () => {
    const future = new Date(Date.now() + 5000).toUTCString()
    const parsed = parseRetryAfterMs(future)

    expect(parsed).toBeGreaterThan(4000)
    expect(parsed).toBeLessThanOrEqual(5000)
  })
})
