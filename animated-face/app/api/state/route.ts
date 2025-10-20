import { MongoClient } from 'mongodb'
import { NextResponse } from 'next/server'

const MONGO_URI = "mongodb+srv://krish:krish@study.po9dv.mongodb.net/"

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const client = new MongoClient(MONGO_URI)
    await client.connect()
    
    const db = client.db('venom')
    const collection = db.collection('state')
    const state = await collection.findOne({}, { projection: { _id: 0 } })
    
    await client.close()
    
    if (state) {
      return NextResponse.json(state)
    } else {
      return NextResponse.json({
        is_active: false,
        is_listening: false,
        is_speaking: false,
        last_command: "",
        timestamp: 0
      })
    }
  } catch (error) {
    console.error('Error fetching from MongoDB:', error)
    return NextResponse.json({
      is_active: false,
      is_listening: false,
      is_speaking: false,
      last_command: "",
      timestamp: 0
    }, { status: 500 })
  }
}
