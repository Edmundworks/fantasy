import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { teams, players } from './schema';
import { eq } from 'drizzle-orm';
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

interface PlayerData {
  playerName: string;
  teamName: string;
  totalAppearances: number;
  totalMinutes: number;
  totalNpxG: number;
  totalXAG: number;
}

async function populatePlayers() {
  try {
    console.log('🔄 Starting to populate players table...');

    // Load players data
    const playersDataPath = path.join(process.cwd(), 'scraper', 'players_from_appearances.json');
    const playersData: PlayerData[] = JSON.parse(fs.readFileSync(playersDataPath, 'utf-8'));
    console.log(`📄 Loaded ${playersData.length} players from appearances data`);

    // Get all teams from database
    const dbTeams = await db.select().from(teams);
    console.log(`🏟️  Found ${dbTeams.length} teams in database`);

    // Create team mapping (name -> id) with normalization
    const teamMap = new Map<string, string>();
    dbTeams.forEach(team => {
      teamMap.set(team.name, team.id);
      
      // Add normalized mappings for appearance data variations
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

    // Process players
    let processedCount = 0;
    let skippedCount = 0;
    const errors: string[] = [];

    for (const playerData of playersData) {
      try {
        const teamId = teamMap.get(playerData.teamName);
        
        if (!teamId) {
          errors.push(`Team not found: ${playerData.teamName} for player ${playerData.playerName}`);
          skippedCount++;
          continue;
        }

        // Check if player already exists
        const existingPlayer = await db
          .select()
          .from(players)
          .where(eq(players.name, playerData.playerName))
          .limit(1);

        if (existingPlayer.length > 0) {
          console.log(`⚠️  Player already exists: ${playerData.playerName}`);
          skippedCount++;
          continue;
        }

        // Insert player (we'll set position/fplPosition as placeholder for now)
        await db.insert(players).values({
          name: playerData.playerName,
          teamId: teamId,
          position: 'Unknown', // Will need to be updated later with actual position data
          fplPosition: 'UNK', // Will need to be updated later with actual FPL position
        });

        processedCount++;
        
        if (processedCount % 50 === 0) {
          console.log(`✅ Processed ${processedCount} players...`);
        }

      } catch (error) {
        errors.push(`Error processing player ${playerData.playerName}: ${error}`);
        skippedCount++;
      }
    }

    console.log('\n📊 Population Summary:');
    console.log(`✅ Successfully processed: ${processedCount} players`);
    console.log(`⚠️  Skipped: ${skippedCount} players`);
    
    if (errors.length > 0) {
      console.log('\n❌ Errors encountered:');
      errors.slice(0, 10).forEach(error => console.log(`  - ${error}`));
      if (errors.length > 10) {
        console.log(`  ... and ${errors.length - 10} more errors`);
      }
    }

    // Show team mapping for reference
    console.log('\n🏟️  Team Mapping Used:');
    Array.from(teamMap.entries()).slice(0, 5).forEach(([name, id]) => {
      console.log(`  ${name} -> ${id.substring(0, 8)}...`);
    });

  } catch (error) {
    console.error('❌ Error populating players:', error);
  } finally {
    await sql.end();
  }
}

populatePlayers();
