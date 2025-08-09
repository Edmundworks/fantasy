CREATE TABLE "appearances" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"season_id" uuid NOT NULL,
	"gameweek_id" uuid NOT NULL,
	"match_id" uuid NOT NULL,
	"team_id" uuid NOT NULL,
	"player_id" uuid NOT NULL,
	"player_fpl_position" varchar(10) NOT NULL,
	"is_clean_eligible" boolean DEFAULT false,
	"minutes" integer DEFAULT 0,
	"started" boolean DEFAULT false,
	"in_squad" boolean DEFAULT false,
	"expected_clean" boolean DEFAULT false,
	"non_penalty_expected_goals" numeric(4, 3),
	"expected_assisted_goals" numeric(4, 3),
	"expected_goal_involvement" numeric(4, 3),
	"expected_non_blank" boolean DEFAULT false,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "gameweeks" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"season_id" uuid NOT NULL,
	"gameweek" integer NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "matches" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"season_id" uuid NOT NULL,
	"gameweek_id" uuid NOT NULL,
	"home_team_id" uuid NOT NULL,
	"home_team_name" varchar(255) NOT NULL,
	"home_team_non_penalty_expected_goals" numeric(4, 3),
	"home_team_expected_clean" boolean DEFAULT false,
	"away_team_id" uuid NOT NULL,
	"away_team_name" varchar(255) NOT NULL,
	"away_team_non_penalty_expected_goals" numeric(4, 3),
	"away_team_expected_clean" boolean DEFAULT false,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "players" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"team_id" uuid NOT NULL,
	"position" varchar(50) NOT NULL,
	"fpl_position" varchar(10) NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "seasons" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"season" varchar(50) NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "teams" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" varchar(255) NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "appearances" ADD CONSTRAINT "appearances_season_id_seasons_id_fk" FOREIGN KEY ("season_id") REFERENCES "public"."seasons"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "appearances" ADD CONSTRAINT "appearances_gameweek_id_gameweeks_id_fk" FOREIGN KEY ("gameweek_id") REFERENCES "public"."gameweeks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "appearances" ADD CONSTRAINT "appearances_match_id_matches_id_fk" FOREIGN KEY ("match_id") REFERENCES "public"."matches"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "appearances" ADD CONSTRAINT "appearances_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "appearances" ADD CONSTRAINT "appearances_player_id_players_id_fk" FOREIGN KEY ("player_id") REFERENCES "public"."players"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "gameweeks" ADD CONSTRAINT "gameweeks_season_id_seasons_id_fk" FOREIGN KEY ("season_id") REFERENCES "public"."seasons"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "matches" ADD CONSTRAINT "matches_season_id_seasons_id_fk" FOREIGN KEY ("season_id") REFERENCES "public"."seasons"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "matches" ADD CONSTRAINT "matches_gameweek_id_gameweeks_id_fk" FOREIGN KEY ("gameweek_id") REFERENCES "public"."gameweeks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "matches" ADD CONSTRAINT "matches_home_team_id_teams_id_fk" FOREIGN KEY ("home_team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "matches" ADD CONSTRAINT "matches_away_team_id_teams_id_fk" FOREIGN KEY ("away_team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "players" ADD CONSTRAINT "players_team_id_teams_id_fk" FOREIGN KEY ("team_id") REFERENCES "public"."teams"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "appearances_season_gameweek_idx" ON "appearances" USING btree ("season_id","gameweek_id");--> statement-breakpoint
CREATE INDEX "appearances_match_idx" ON "appearances" USING btree ("match_id");--> statement-breakpoint
CREATE INDEX "appearances_player_idx" ON "appearances" USING btree ("player_id");--> statement-breakpoint
CREATE INDEX "appearances_team_idx" ON "appearances" USING btree ("team_id");--> statement-breakpoint
CREATE INDEX "gameweeks_season_gameweek_idx" ON "gameweeks" USING btree ("season_id","gameweek");--> statement-breakpoint
CREATE INDEX "matches_season_gameweek_idx" ON "matches" USING btree ("season_id","gameweek_id");--> statement-breakpoint
CREATE INDEX "matches_home_team_idx" ON "matches" USING btree ("home_team_id");--> statement-breakpoint
CREATE INDEX "matches_away_team_idx" ON "matches" USING btree ("away_team_id");--> statement-breakpoint
CREATE INDEX "players_team_idx" ON "players" USING btree ("team_id");--> statement-breakpoint
CREATE INDEX "players_position_idx" ON "players" USING btree ("position");--> statement-breakpoint
CREATE INDEX "players_fpl_position_idx" ON "players" USING btree ("fpl_position");--> statement-breakpoint
CREATE INDEX "seasons_season_idx" ON "seasons" USING btree ("season");--> statement-breakpoint
CREATE INDEX "teams_name_idx" ON "teams" USING btree ("name");