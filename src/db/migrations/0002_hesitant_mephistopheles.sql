DROP TABLE IF EXISTS gameweeks CASCADE;
ALTER TABLE appearances DROP CONSTRAINT IF EXISTS appearances_gameweek_id_gameweeks_id_fk;
--> statement-breakpoint
ALTER TABLE matches DROP CONSTRAINT IF EXISTS matches_gameweek_id_gameweeks_id_fk;
--> statement-breakpoint
DROP INDEX IF EXISTS appearances_season_gameweek_idx;--> statement-breakpoint
DROP INDEX IF EXISTS matches_season_gameweek_idx;--> statement-breakpoint
ALTER TABLE matches ADD COLUMN IF NOT EXISTS gameweek integer;--> statement-breakpoint
CREATE INDEX "appearances_season_idx" ON "appearances" USING btree ("season_id");--> statement-breakpoint
CREATE INDEX "matches_season_idx" ON "matches" USING btree ("season_id");--> statement-breakpoint
CREATE INDEX "matches_season_gameweek_idx" ON "matches" USING btree ("season_id","gameweek");--> statement-breakpoint
ALTER TABLE appearances DROP COLUMN IF EXISTS gameweek_id;--> statement-breakpoint
ALTER TABLE matches DROP COLUMN IF EXISTS gameweek_id;