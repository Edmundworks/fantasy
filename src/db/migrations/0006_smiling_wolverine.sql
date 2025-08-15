CREATE TABLE "2425players" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"player_id" uuid NOT NULL,
	"team_id" uuid NOT NULL,
	"name" varchar(255) NOT NULL,
	"team_name" varchar(255) NOT NULL,
	"fpl_position" varchar(10) NOT NULL,
	"price" numeric(4, 1),
	"in_squad" integer DEFAULT 0 NOT NULL,
	"total_starts" integer DEFAULT 0 NOT NULL,
	"total_minutes" integer DEFAULT 0 NOT NULL,
	"total_expected_non_blanks" integer DEFAULT 0 NOT NULL,
	"non_blanks_per_squad" numeric(4, 3) DEFAULT '0',
	"non_blanks_per_start" numeric(4, 3) DEFAULT '0',
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "2425players" ADD CONSTRAINT "2425players_player_id_players_id_fk" FOREIGN KEY ("player_id") REFERENCES "public"."players"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "2425players" ADD CONSTRAINT "2425players_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "2425players_player_idx" ON "2425players" USING btree ("player_id");--> statement-breakpoint
CREATE INDEX "2425players_team_idx" ON "2425players" USING btree ("team_id");--> statement-breakpoint
CREATE INDEX "2425players_position_idx" ON "2425players" USING btree ("fpl_position");--> statement-breakpoint
CREATE INDEX "2425players_price_idx" ON "2425players" USING btree ("price");