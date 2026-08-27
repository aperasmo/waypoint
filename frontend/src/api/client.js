/**
 * Base URL for the Waypoint API.
 *
 * Vite environment variables allow each deployment to use a different
 * backend without changing application source code.
 */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8100"

/**
 * Represents an HTTP error returned by the Waypoint API.
 *
 * Keeping the status code lets individual features distinguish expected
 * responses such as 404 from genuine server failures such as 500.
 */
export class ApiError extends Error {
  constructor(message, status, statusText) {
    super(message)

    this.name = "ApiError"
    this.status = status
    this.statusText = statusText
  }
}

/**
 * Fetch JSON from the Waypoint API with consistent HTTP error handling.
 *
 * fetch() rejects automatically for network failures, but HTTP responses
 * such as 404 and 500 still resolve. We therefore check response.ok and
 * convert unsuccessful HTTP responses into ApiError instances.
 *
 * @param {string} path - API path beginning with "/".
 * @param {RequestInit} [options] - Standard fetch configuration.
 * @returns {Promise<unknown>} Parsed JSON response.
 * @throws {ApiError} When the server returns a non-success HTTP status.
 */
export async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options)

  if (!response.ok) {
    throw new ApiError(
      `Waypoint API request failed: ${response.status} ${response.statusText}`,
      response.status,
      response.statusText,
    )
  }

  return response.json()
}