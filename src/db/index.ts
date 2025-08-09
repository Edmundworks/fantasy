import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';

const client = postgres(process.env.DATABASE_URL!, {
  prepare: false, // required for pgbouncer/transaction pooler
  ssl: 'require', // enforce TLS for Supabase
});
export const db = drizzle(client);
