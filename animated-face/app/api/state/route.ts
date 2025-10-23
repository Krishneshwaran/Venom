import { MongoClient } from 'mongodb'
import { NextResponse } from 'next/server'

const MONGO_URI = "mongodb+srv://krish:krish@study.po9dv.mongodb.net/"

export const dynamic = 'force-dynamic'
export const revalidate = 0

let cachedClient: MongoClient | null = null

async function getMongoClient() {
  if (cachedClient) {
    return cachedClient
  }

  const client = new MongoClient(MONGO_URI, {
    serverSelectionTimeoutMS: 5000,
    connectTimeoutMS: 5000,
  })

  await client.connect()
  cachedClient = client
  return client
}

export async function GET(request: Request) {
  try {
    // Log some request info (helps diagnose redirect loops from proxies/origins)
    const host = request.headers.get('host')
    const origin = request.headers.get('origin')
    const referer = request.headers.get('referer')
    console.log('[api/state] incoming request', { host, origin, referer })
  } catch (e) {
    // best-effort logging, don't crash the route
    console.error('[api/state] logging error', e)
  }
  try {
    const client = await getMongoClient()

    const db = client.db('venom')
    const collection = db.collection('state')
    const state = await collection.findOne({}, { projection: { _id: 0 } })

    if (state && state.is_active !== undefined) {
      return NextResponse.json({ is_active: state.is_active }, {
        headers: {
          'Cache-Control': 'no-store, must-revalidate',
          'Content-Type': 'application/json',
        }
      })
    } else {
      return NextResponse.json({ is_active: false }, {
        headers: {
          'Cache-Control': 'no-store, must-revalidate',
          'Content-Type': 'application/json',
        }
      })
    }
  } catch (error) {
    console.error('Error fetching from MongoDB:', error)
    return NextResponse.json({ is_active: false }, {
      status: 200,
      headers: {
        'Cache-Control': 'no-store, must-revalidate',
        'Content-Type': 'application/json',
      }
    })
  }
}
