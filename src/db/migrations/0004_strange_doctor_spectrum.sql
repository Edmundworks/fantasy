ALTER TABLE "players" ADD COLUMN "name" varchar(255) NOT NULL;--> statement-breakpoint
CREATE INDEX "players_name_idx" ON "players" USING btree ("name");