import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { eq, and } from 'drizzle-orm';
import * as fs from 'fs';
import * as path from 'path';
import { config } from 'dotenv';

// Load environment variables from .env.local (one directory up)
config({ path: path.join(__dirname, '../.env.local') });

// Import schema from the parent directory
import { matches, teams, seasons } from '../src/db/schema';

// Database connection
const client = postgres(process.env.DATABASE_URL!, {
  prepare: false,
  ssl: 'require',
});
const db = drizzle(client);

interface MatchData {
  gameweek: number;
  home_team: string;
  away_team: string;
  match_report_url: string | null;
}

// Team name mapping to handle variations in FBref vs our database
const TEAM_NAME_MAPPING: Record<string, string> = {
  'Manchester Utd': 'Manchester United',
  'Newcastle Utd': 'Newcastle United', 
  'Nott\'ham Forest': 'Nottingham Forest',
  'Wolves': 'Wolverhampton Wanderers',
  'Tottenham': 'Tottenham Hotspur',
  'Leicester City': 'Leicester',
  'Brighton': 'Brighton and Hove Albion',
};

function normalizeTeamName(teamName: string): string {
  return TEAM_NAME_MAPPING[teamName] || teamName;
}

async function ensureSeasonExists(seasonName: string = '2024-2025') {
  console.log(`🔍 Checking if season ${seasonName} exists...`);
  
  const existingSeason = await db.select().from(seasons).where(eq(seasons.season, seasonName)).limit(1);
  
  if (existingSeason.length === 0) {
    console.log(`➕ Creating season: ${seasonName}`);
    const [newSeason] = await db.insert(seasons).values({
      season: seasonName,
    }).returning();
    return newSeason.id;
  }
  
  console.log(`✅ Season ${seasonName} already exists`);
  return existingSeason[0].id;
}

// Gameweeks are now just numbers stored directly in matches table

async function ensureTeamExists(teamName: string) {
  const normalizedName = normalizeTeamName(teamName);
  
  const existingTeam = await db.select().from(teams).where(eq(teams.name, normalizedName)).limit(1);
  
  if (existingTeam.length === 0) {
    console.log(`➕ Creating team: ${normalizedName}`);
    const [newTeam] = await db.insert(teams).values({
      name: normalizedName,
    }).returning();
    return newTeam.id;
  }
  
  return existingTeam[0].id;
}

async function processMatchesData() {
  try {
    console.log('🚀 Starting match data processing...\n');
    
    // Read the JSON file created by matchreports.py
    const jsonFilePath = path.join(__dirname, 'premier_league_matches_2024_2025.json');
    
    if (!fs.existsSync(jsonFilePath)) {
      console.error('❌ JSON file not found: premier_league_matches_2024_2025.json');
      console.log('💡 Run the matchreports.py script first to generate the data:');
      console.log('   python matchreports.py');
      return;
    }
    
    const jsonData = fs.readFileSync(jsonFilePath, 'utf8');
    const matchesData: MatchData[] = JSON.parse(jsonData);
    
    console.log(`📊 Found ${matchesData.length} matches to process\n`);
    
    // Ensure season exists
    const seasonId = await ensureSeasonExists('2024-2025');
    console.log(`📅 Using season ID: ${seasonId}\n`);
    
    // Create cache to avoid repeated database calls
    const teamCache = new Map<string, string>();
    
    let processedCount = 0;
    let skippedCount = 0;
    
    for (const matchData of matchesData) {
      try {
        console.log(`📝 Processing match ${processedCount + skippedCount + 1}/${matchesData.length}: ${matchData.home_team} vs ${matchData.away_team} (GW${matchData.gameweek})`);
        
        // Get or create teams
        let homeTeamId = teamCache.get(matchData.home_team);
        if (!homeTeamId) {
          homeTeamId = await ensureTeamExists(matchData.home_team);
          teamCache.set(matchData.home_team, homeTeamId);
        }
        
        let awayTeamId = teamCache.get(matchData.away_team);
        if (!awayTeamId) {
          awayTeamId = await ensureTeamExists(matchData.away_team);
          teamCache.set(matchData.away_team, awayTeamId);
        }
        
        // Check if match already exists
        const existingMatch = await db.select().from(matches)
          .where(and(
            eq(matches.seasonId, seasonId),
            eq(matches.homeTeamId, homeTeamId),
            eq(matches.awayTeamId, awayTeamId)
          ))
          .limit(1);
        
        if (existingMatch.length > 0) {
          console.log(`⏭️  Match already exists, skipping...`);
          skippedCount++;
          continue;
        }
        
        // Convert relative URL to full URL if needed
        let fullMatchReportUrl = matchData.match_report_url;
        if (fullMatchReportUrl && fullMatchReportUrl.startsWith('/')) {
          fullMatchReportUrl = `https://fbref.com${fullMatchReportUrl}`;
        }
        
        // Insert the match
        await db.insert(matches).values({
          seasonId,
          gameweek: matchData.gameweek,
          homeTeamId,
          homeTeamName: normalizeTeamName(matchData.home_team),
          awayTeamId,
          awayTeamName: normalizeTeamName(matchData.away_team),
          matchReportUrl: fullMatchReportUrl,
        });
        
        console.log(`✅ Match inserted successfully`);
        processedCount++;
        
      } catch (error) {
        console.error(`❌ Error processing match: ${error}`);
        continue;
      }
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('📊 PROCESSING COMPLETE');
    console.log('='.repeat(60));
    console.log(`✅ Successfully processed: ${processedCount} matches`);
    console.log(`⏭️  Skipped (already exist): ${skippedCount} matches`);
    console.log(`🎯 Total matches in file: ${matchesData.length}`);
    console.log('='.repeat(60));
    
  } catch (error) {
    console.error('❌ Error processing matches data:', error);
  } finally {
    // Close database connection
    await client.end();
  }
}

// Run the script
if (require.main === module) {
  processMatchesData();
}

export { processMatchesData };