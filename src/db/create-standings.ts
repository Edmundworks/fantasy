import 'dotenv/config';
import { db } from './index';
import { sql } from 'drizzle-orm';

async function main(): Promise<void> {
  // Create table if not exists
  await db.execute(sql`
    CREATE TABLE IF NOT EXISTS "standings" (
      "id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
      "season_id" uuid NOT NULL,
      "season" varchar(50) NOT NULL,
      "team_id" uuid NOT NULL,
      "team_name" varchar(255) NOT NULL,
      "expected_cleans" integer DEFAULT 0 NOT NULL,
      "created_at" timestamp DEFAULT now() NOT NULL,
      "updated_at" timestamp DEFAULT now() NOT NULL
    );
  `);

  // Add FK to seasons if missing
  await db.execute(sql`
    DO $$ BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'standings_season_id_seasons_id_fk'
      ) THEN
        ALTER TABLE "standings"
        ADD CONSTRAINT "standings_season_id_seasons_id_fk"
        FOREIGN KEY ("season_id") REFERENCES "public"."seasons"("id")
        ON UPDATE NO ACTION ON DELETE NO ACTION;
      END IF;
    END $$;
  `);

  // Add FK to teams if missing
  await db.execute(sql`
    DO $$ BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'standings_team_id_teams_id_fk'
      ) THEN
        ALTER TABLE "standings"
        ADD CONSTRAINT "standings_team_id_teams_id_fk"
        FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id")
        ON UPDATE NO ACTION ON DELETE NO ACTION;
      END IF;
    END $$;
  `);

  // Indexes
  await db.execute(sql`CREATE INDEX IF NOT EXISTS "standings_season_idx" ON "standings" ("season_id");`);
  await db.execute(sql`CREATE INDEX IF NOT EXISTS "standings_team_idx" ON "standings" ("team_id");`);

  // eslint-disable-next-line no-console
  console.log('standings table ensured');
}

main().catch((e) => {
  // eslint-disable-next-line no-console
  console.error(e);
  process.exit(1);
});