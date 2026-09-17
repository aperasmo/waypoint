import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { db } from './db.js'
import { browse } from './routes/browse.js'

export const app = new Hono()

app.get('/health/db', async (c) => {
  const result = await db.query<{ section_count: number }>(
    'SELECT COUNT(*)::int AS section_count FROM sections',
  )

  return c.json({
    database: 'ok',
    section_count: result.rows[0].section_count,
  })
})

app.use(
  '/browse/*',
  cors({
    origin: 'http://localhost:5174',
    allowMethods: ['GET', 'OPTIONS'],
  }),
)

app.route('/browse', browse)