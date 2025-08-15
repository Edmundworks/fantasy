import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { teams, players, matches, appearances } from './schema';
import { eq, and } from 'drizzle-orm';
import fs from 'fs';
import path from 'path';

// Database connection
const connectionString = process.env.DATABASE_URL;
if (!connectionString) {
  console.error('DATABASE_URL environment variable is required');
  process.exit(1);
}

const sql = postgres(connectionString);
const db = drizzle(sql);

// Fixed season ID as provided
const SEASON_ID = 'dad65c20-e3e6-42f3-9579-0eae9026f338';

interface AppearanceData {
  matchId: string;
  matchUrl: string;
  playerName: string;
  teamName: string;
  in_squad: boolean;
  started: boolean;
  minutes_played: number | null;
  npXg: number;
  xAG: number;
}

async function populateAppearances() {
  try {
    console.log('🔄 Starting to populate appearances table...');

    // Load appearance data
    const appearanceDataPath = path.join(process.cwd(), 'scraper', 'appearance_data_normalized.json');
    const appearanceData: AppearanceData[] = JSON.parse(fs.readFileSync(appearanceDataPath, 'utf-8'));
    console.log(`📄 Loaded ${appearanceData.length} appearance records`);

    // Get all teams, players, and matches for mapping
    console.log('🔍 Loading database mappings...');
    const [dbTeams, dbPlayers, dbMatches] = await Promise.all([
      db.select().from(teams),
      db.select().from(players),
      db.select().from(matches)
    ]);

    console.log(`🏟️  Found ${dbTeams.length} teams`);
    console.log(`👥 Found ${dbPlayers.length} players`);
    console.log(`⚽ Found ${dbMatches.length} matches`);

    // Create mappings
    const teamMap = new Map<string, string>();
    dbTeams.forEach(team => {
      teamMap.set(team.name, team.id);
      // Add normalized mappings
      if (team.name === 'Brighton and Hove Albion') {
        teamMap.set('Brighton', team.id);
      } else if (team.name === 'Leicester') {
        teamMap.set('Leicester City', team.id);
      } else if (team.name === 'Nottingham Forest') {
        teamMap.set("Nott'ham Forest", team.id);
      } else if (team.name === 'Tottenham Hotspur') {
        teamMap.set('Tottenham', team.id);
      }
    });

    const playerMap = new Map<string, string>();
    dbPlayers.forEach(player => {
      playerMap.set(player.name, player.id);
    });

    const matchMap = new Map<string, string>();
    dbMatches.forEach(match => {
      // Extract match ID from the URL path (e.g., /matches/cc5b4244/ -> cc5b4244)
      if (match.matchReportUrl) {
        const urlMatch = match.matchReportUrl.match(/\/matches\/([^\/]+)\//);
        if (urlMatch) {
          matchMap.set(urlMatch[1], match.id);
        }
      }
    });

    console.log(`🗺️  Created mappings: ${teamMap.size} teams, ${playerMap.size} players, ${matchMap.size} matches`);

    // Process appearances in batches
    const BATCH_SIZE = 100;
    let processedCount = 0;
    let skippedCount = 0;
    const errors: string[] = [];

    for (let i = 0; i < appearanceData.length; i += BATCH_SIZE) {
      const batch = appearanceData.slice(i, i + BATCH_SIZE);
      const insertData: any[] = [];

      for (const appearance of batch) {
        try {
          // Get required IDs
          const teamId = teamMap.get(appearance.teamName);
          const playerId = playerMap.get(appearance.playerName);
          const matchId = matchMap.get(appearance.matchId);

          if (!teamId) {
            errors.push(`Team not found: ${appearance.teamName}`);
            skippedCount++;
            continue;
          }

          if (!playerId) {
            errors.push(`Player not found: ${appearance.playerName}`);
            skippedCount++;
            continue;
          }

          if (!matchId) {
            errors.push(`Match not found: ${appearance.matchId}`);
            skippedCount++;
            continue;
          }

          // Calculate expected goal involvement (npXg + xAG)
          const expectedGoalInvolvement = appearance.npXg + appearance.xAG;

          // Prepare insert data
          const insertRecord = {
            seasonId: SEASON_ID,
            matchId: matchId,
            teamId: teamId,
            playerId: playerId,
            playerFplPosition: 'UNK', // Placeholder - will need to be updated later
            isCleanEligible: false, // Will be calculated later based on position and minutes
            minutes: appearance.minutes_played || 0,
            started: appearance.started,
            inSquad: appearance.in_squad,
            expectedClean: false, // Will be calculated later based on match clean sheet
            nonPenaltyExpectedGoals: appearance.npXg.toString(),
            expectedAssistedGoals: appearance.xAG.toString(),
            expectedGoalInvolvement: expectedGoalInvolvement.toString(),
            expectedNonBlank: false, // Will be calculated later
          };

          insertData.push(insertRecord);

        } catch (error) {
          errors.push(`Error processing appearance for ${appearance.playerName}: ${error}`);
          skippedCount++;
        }
      }

      // Insert batch
      if (insertData.length > 0) {
        try {
          await db.insert(appearances).values(insertData);
          processedCount += insertData.length;
        } catch (error) {
          errors.push(`Error inserting batch: ${error}`);
          skippedCount += insertData.length;
        }
      }

      // Progress update
      if ((i + BATCH_SIZE) % 1000 === 0 || i + BATCH_SIZE >= appearanceData.length) {
        console.log(`✅ Processed ${Math.min(i + BATCH_SIZE, appearanceData.length)}/${appearanceData.length} records (${processedCount} inserted, ${skippedCount} skipped)`);
      }
    }

    console.log('\n📊 Population Summary:');
    console.log(`✅ Successfully processed: ${processedCount} appearances`);
    console.log(`⚠️  Skipped: ${skippedCount} appearances`);
    
    if (errors.length > 0) {
      console.log(`\n❌ Errors encountered: ${errors.length}`);
      // Show first 10 errors
      errors.slice(0, 10).forEach(error => console.log(`  - ${error}`));
      if (errors.length > 10) {
        console.log(`  ... and ${errors.length - 10} more errors`);
      }
    }

  } catch (error) {
    console.error('❌ Error populating appearances:', error);
  } finally {
    await sql.end();
  }
}

populateAppearances();
