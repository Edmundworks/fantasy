// src/db/schema.ts
import { pgTable, uuid, varchar, integer, decimal, timestamp, boolean, text, date, index } from 'drizzle-orm/pg-core';

// Teams table
export const teams = pgTable('teams', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: varchar('name', { length: 255 }).notNull(),
  created_at: timestamp('created_at').defaultNow().notNull(),
  updated_at: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  nameIdx: index('teams_name_idx').on(table.name),
}));

// Seasons table
export const seasons = pgTable('seasons', {
  id: uuid('id').primaryKey().defaultRandom(),
  season: varchar('season', { length: 50 }).notNull(), // e.g., "2024-2025"
  created_at: timestamp('created_at').defaultNow().notNull(),
  updated_at: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  seasonIdx: index('seasons_season_idx').on(table.season),
}));

// Gameweeks table removed - using optional gameweek field in matches instead

// Players table
export const players = pgTable('players', {
  id: uuid('id').primaryKey().defaultRandom(),
  name: varchar('name', { length: 255 }).notNull(),
  teamId: uuid('team_id').notNull().references(() => teams.id),
  position: varchar('position', { length: 50 }).notNull(), // e.g., "Forward", "Midfielder", "Defender", "Goalkeeper"
  fplPosition: varchar('fpl_position', { length: 10 }).notNull(), // e.g., "FWD", "MID", "DEF", "GK"
  price: decimal('price', { precision: 4, scale: 1 }), // FPL price, e.g., 4.0, 10.5
  created_at: timestamp('created_at').defaultNow().notNull(),
  updated_at: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  nameIdx: index('players_name_idx').on(table.name),
  teamIdx: index('players_team_idx').on(table.teamId),
  positionIdx: index('players_position_idx').on(table.position),
  fplPositionIdx: index('players_fpl_position_idx').on(table.fplPosition),
}));

// Matches table
export const matches = pgTable('matches', {
  id: uuid('id').primaryKey().defaultRandom(),
  seasonId: uuid('season_id').notNull().references(() => seasons.id),
  gameweek: integer('gameweek'), // optional gameweek number
  homeTeamId: uuid('home_team_id').notNull().references(() => teams.id),
  homeTeamName: varchar('home_team_name', { length: 255 }).notNull(),
  homeTeamNonPenaltyExpectedGoals: decimal('home_team_non_penalty_expected_goals', { precision: 4, scale: 3 }),
  homeTeamExpectedClean: boolean('home_team_expected_clean').default(false),
  awayTeamId: uuid('away_team_id').notNull().references(() => teams.id),
  awayTeamName: varchar('away_team_name', { length: 255 }).notNull(),
  awayTeamNonPenaltyExpectedGoals: decimal('away_team_non_penalty_expected_goals', { precision: 4, scale: 3 }),
  awayTeamExpectedClean: boolean('away_team_expected_clean').default(false),
  matchReportUrl: varchar('match_report_url', { length: 500 }),
  created_at: timestamp('created_at').defaultNow().notNull(),
  updated_at: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  seasonIdx: index('matches_season_idx').on(table.seasonId),
  seasonGameweekIdx: index('matches_season_gameweek_idx').on(table.seasonId, table.gameweek),
  homeTeamIdx: index('matches_home_team_idx').on(table.homeTeamId),
  awayTeamIdx: index('matches_away_team_idx').on(table.awayTeamId),
}));

// Appearances table
export const appearances = pgTable('appearances', {
  id: uuid('id').primaryKey().defaultRandom(),
  seasonId: uuid('season_id').notNull().references(() => seasons.id),
  matchId: uuid('match_id').notNull().references(() => matches.id),
  teamId: uuid('team_id').notNull().references(() => teams.id),
  playerId: uuid('player_id').notNull().references(() => players.id),
  playerFplPosition: varchar('player_fpl_position', { length: 10 }).notNull(),
  isCleanEligible: boolean('is_clean_eligible').default(false),
  minutes: integer('minutes').default(0),
  started: boolean('started').default(false),
  inSquad: boolean('in_squad').default(false),
  expectedClean: boolean('expected_clean').default(false),
  nonPenaltyExpectedGoals: decimal('non_penalty_expected_goals', { precision: 4, scale: 3 }),
  expectedAssistedGoals: decimal('expected_assisted_goals', { precision: 4, scale: 3 }),
  expectedGoalInvolvement: decimal('expected_goal_involvement', { precision: 4, scale: 3 }),
  expectedNonBlank: boolean('expected_non_blank').default(false),
  created_at: timestamp('created_at').defaultNow().notNull(),
  updated_at: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  seasonIdx: index('appearances_season_idx').on(table.seasonId),
  matchIdx: index('appearances_match_idx').on(table.matchId),
  playerIdx: index('appearances_player_idx').on(table.playerId),
  teamIdx: index('appearances_team_idx').on(table.teamId),
}));

// Standings table
export const standings = pgTable('standings', {
  id: uuid('id').primaryKey().defaultRandom(),
  seasonId: uuid('season_id').notNull().references(() => seasons.id),
  season: varchar('season', { length: 50 }).notNull(),
  teamId: uuid('team_id').notNull().references(() => teams.id),
  teamName: varchar('team_name', { length: 255 }).notNull(),
  expectedCleans: integer('expected_cleans').notNull().default(0),
  created_at: timestamp('created_at').defaultNow().notNull(),
  updated_at: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  standingsSeasonIdx: index('standings_season_idx').on(table.seasonId),
  standingsTeamIdx: index('standings_team_idx').on(table.teamId),
}));

// 2024-25 Players summary table
export const players2425 = pgTable('2425players', {
  id: uuid('id').primaryKey().defaultRandom(),
  playerId: uuid('player_id').notNull().references(() => players.id),
  teamId: uuid('team_id').notNull().references(() => teams.id),
  name: varchar('name', { length: 255 }).notNull(),
  teamName: varchar('team_name', { length: 255 }).notNull(),
  fplPosition: varchar('fpl_position', { length: 10 }).notNull(),
  price: decimal('price', { precision: 4, scale: 1 }),
  inSquad: integer('in_squad').notNull().default(0), // Total times in squad
  totalStarts: integer('total_starts').notNull().default(0), // Total times started
  totalMinutes: integer('total_minutes').notNull().default(0), // Sum of minutes
  totalExpectedNonBlanks: integer('total_expected_non_blanks').notNull().default(0), // Count of expected non-blanks
  nonBlanksPerSquad: decimal('non_blanks_per_squad', { precision: 4, scale: 3 }).default('0'), // Expected non-blanks / times in squad
  nonBlanksPerStart: decimal('non_blanks_per_start', { precision: 4, scale: 3 }).default('0'), // Expected non-blanks / starts
  created_at: timestamp('created_at').defaultNow().notNull(),
  updated_at: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  playerIdx: index('2425players_player_idx').on(table.playerId),
  teamIdx: index('2425players_team_idx').on(table.teamId),
  positionIdx: index('2425players_position_idx').on(table.fplPosition),
  priceIdx: index('2425players_price_idx').on(table.price),
}));