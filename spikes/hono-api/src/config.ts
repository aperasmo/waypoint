import { existsSync } from 'node:fs'
import path from 'node:path'
import { loadEnvFile } from 'node:process'
import { fileURLToPath } from 'node:url'

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const envPath = path.resolve(currentDir, '../.env')

if (existsSync(envPath)) {
  loadEnvFile(envPath)
}

const databaseUrl = process.env.DATABASE_URL

if (!databaseUrl) {
  throw new Error('DATABASE_URL is required')
}

export const config = {
  databaseUrl,
  corsOrigin: process.env.CORS_ORIGIN ?? 'http://localhost:5174',
}