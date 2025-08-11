ALTER TABLE "gameweeks" DISABLE ROW LEVEL SECURITY;--> statement-breakpoint
DROP TABLE "gameweeks" CASCADE;--> statement-breakpoint
ALTER TABLE "appearances" DROP CONSTRAINT "appearances_gameweek_id_gameweeks_id_fk";
--> statement-breakpoint
ALTER TABLE "matches" DROP CONSTRAINT "matches_gameweek_id_gameweeks_id_fk";
--> statement-breakpoint
DROP INDEX "appearances_season_gameweek_idx";--> statement-breakpoint
DROP INDEX "matches_season_gameweek_idx";--> statement-breakpoint
ALTER TABLE "matches" ADD COLUMN "gameweek" integer;--> statement-breakpoint
CREATE INDEX "appearances_season_idx" ON "appearances" USING btree ("season_id");--> statement-breakpoint
CREATE INDEX "matches_season_idx" ON "matches" USING btree ("season_id");--> statement-breakpoint
CREATE INDEX "matches_season_gameweek_idx" ON "matches" USING btree ("season_id","gameweek");--> statement-breakpoint
ALTER TABLE "appearances" DROP COLUMN "gameweek_id";--> statement-breakpoint
ALTER TABLE "matches" DROP COLUMN "gameweek_id";