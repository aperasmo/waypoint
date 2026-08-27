import { fetchJson } from "@/api/client"

/**
 * Sends a policy question to Waypoint's /ask endpoint.
 *
 * This module knows the /ask contract, while client.js handles generic
 * HTTP behaviour shared across the frontend.
 *
 * @param {string} question - The user's submitted immigration question.
 * @param {AbortSignal} [signal] - Optional signal for cancelling the request.
 * @returns {Promise<object>} The parsed /ask response.
 */
export async function askWaypoint(question, signal) {
  return fetchJson("/ask", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify({
      question,
    }),

    signal,
  })
}