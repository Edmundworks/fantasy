import 'dotenv/config';
import { db } from './index';
import { sql } from 'drizzle-orm';

async function main(): Promise<void> {
  // Enable RLS on standings table
  await db.execute(sql`ALTER TABLE "standings" ENABLE ROW LEVEL SECURITY;`);
  
  // Drop existing policy if it exists and create new one
  try {
    await db.execute(sql`DROP POLICY IF EXISTS "Allow all for authenticated users" ON "standings";`);
  } catch (e) {
    // Policy might not exist, ignore error
  }
  
  // Create a policy to allow all operations for authenticated users
  await db.execute(sql`
    CREATE POLICY "Allow all for authenticated users" ON "standings"
    FOR ALL USING (auth.role() = 'authenticated');
  `);

  console.log('Row Level Security enabled for standings table');
  console.log('Policy created for authenticated users');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});