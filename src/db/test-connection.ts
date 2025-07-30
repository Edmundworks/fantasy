// src/db/test-connection.ts
import { config } from 'dotenv';

// Load environment variables from .env.local FIRST
config({ path: '.env.local' });

import { db } from './index';
import { sql } from 'drizzle-orm';

export async function testConnection() {
  console.log('DATABASE_URL exists:', !!process.env.DATABASE_URL);
  console.log('DATABASE_URL preview:', process.env.DATABASE_URL?.substring(0, 30) + '...');
  
  try {
    const result = await db.execute(sql`SELECT NOW()`);
    console.log('✅ Database connected successfully!');
    console.log('Current time from database:', result[0]);
    return true;
  } catch (error) {
    console.error('❌ Database connection failed:');
    console.error(error);
    return false;
  }
}

// Run the test
testConnection();