import { Pool } from 'pg'

import { config } from './config.js'

export const db = new Pool({
  connectionString: config.databaseUrl,
  connectionTimeoutMillis: 5000,
})

db.on('error', (error) => {
  console.error('Unexpected PostgreSQL pool error:', error)
})