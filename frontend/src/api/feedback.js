import { fetchJson } from "@/api/client"

/**
 * Sends anonymous coverage feedback to Waypoint's /feedback endpoint.
 *
 * This module knows the /feedback contract, while client.js handles generic
 * HTTP behaviour shared across the frontend.
 *
 * @param {object} payload - Feedback fields (question, feedback_type, etc.).
 * @returns {Promise<object>} The parsed /feedback response.
 */
export async function submitFeedback(payload) {
  return fetchJson("/feedback", {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
    },

    body: JSON.stringify(payload),
  })
}
