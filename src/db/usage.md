to test DB
DATABASE_URL=postgresql://postgres.smqlcqtbqnwhmkikigqb:j2XUqsqsEH1Mf4CO@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require npm run test-db

to run migrations
DATABASE_URL=postgresql://postgres.smqlcqtbqnwhmkikigqb:j2XUqsqsEH1Mf4CO@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require npx drizzle-kit migrate