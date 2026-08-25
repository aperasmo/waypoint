/**
 * Base URL for the Waypoint backend.
 *
 * Vite exposes browser-safe environment variables that begin with `VITE_`.
 * The localhost fallback keeps local development working without requiring
 * an environment file.
 */
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8100"

/**
 * Sends a policy question to Waypoint's production /ask endpoint.
 *
 * This function is responsible only for HTTP communication. It does not
 * interpret evidence status or make any policy decisions.
 *
 * @param {string} question - The user's submitted question.
 * @param {AbortSignal} [signal] - Optional signal for cancelling the request.
 * @returns {Promise<object>} The parsed /ask response.
 * @throws {Error} When the server cannot return a successful response.
 */
export async function askWaypoint(question, signal) {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      question,
    }),

    signal,
  })

  /**
   * A fetch request only rejects automatically for network-level failures.
   * HTTP responses such as 400 or 500 still resolve, so response.ok must
   * be checked explicitly.
   */
  if (!response.ok) {
    throw new Error(`Ask request failed with status ${response.status}`)
  }

  return response.json()
}