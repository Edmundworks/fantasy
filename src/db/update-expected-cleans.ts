import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { matches, appearances } from './schema';
import { eq, and, gte } from 'drizzle-orm';

// Database connection
const connectionString = process.env.DATABASE_URL;
if (!connectionString) {
  console.error('DATABASE_URL environment variable is required');
  process.exit(1);
}

const sql = postgres(connectionString);
const db = drizzle(sql);

async function updateExpectedCleans() {
  try {
    console.log('🔄 Starting to update expected clean flags in appearances...');

    // Step 1: Get all matches where home team has expected clean
    console.log('🏠 Finding matches where home team has expected clean...');
    const homeCleanMatches = await db
      .select({
        matchId: matches.id,
        homeTeamId: matches.homeTeamId,
        homeTeamName: matches.homeTeamName
      })
      .from(matches)
      .where(eq(matches.homeTeamExpectedClean, true));

    console.log(`📊 Found ${homeCleanMatches.length} matches where home team has expected clean`);

    // Step 2: Update appearances for home team expected cleans
    let homeUpdatedCount = 0;
    for (const match of homeCleanMatches) {
      try {
        const result = await db
          .update(appearances)
          .set({ expectedClean: true })
          .where(
            and(
              eq(appearances.matchId, match.matchId),
              eq(appearances.teamId, match.homeTeamId),
              eq(appearances.started, true),
              gte(appearances.minutes, 60)
            )
          );

        // Note: postgres-js doesn't return rowCount, so we'll track matches processed
        homeUpdatedCount++;
        
        if (homeUpdatedCount % 50 === 0) {
          console.log(`✅ Processed ${homeUpdatedCount}/${homeCleanMatches.length} home team matches...`);
        }
      } catch (error) {
        console.error(`❌ Error updating home team appearances for match ${match.homeTeamName}: ${error}`);
      }
    }

    console.log(`✅ Completed home team updates: ${homeUpdatedCount} matches processed`);

    // Step 3: Get all matches where away team has expected clean
    console.log('\n✈️  Finding matches where away team has expected clean...');
    const awayCleanMatches = await db
      .select({
        matchId: matches.id,
        awayTeamId: matches.awayTeamId,
        awayTeamName: matches.awayTeamName
      })
      .from(matches)
      .where(eq(matches.awayTeamExpectedClean, true));

    console.log(`📊 Found ${awayCleanMatches.length} matches where away team has expected clean`);

    // Step 4: Update appearances for away team expected cleans
    let awayUpdatedCount = 0;
    for (const match of awayCleanMatches) {
      try {
        const result = await db
          .update(appearances)
          .set({ expectedClean: true })
          .where(
            and(
              eq(appearances.matchId, match.matchId),
              eq(appearances.teamId, match.awayTeamId),
              eq(appearances.started, true),
              gte(appearances.minutes, 60)
            )
          );

        awayUpdatedCount++;
        
        if (awayUpdatedCount % 50 === 0) {
          console.log(`✅ Processed ${awayUpdatedCount}/${awayCleanMatches.length} away team matches...`);
        }
      } catch (error) {
        console.error(`❌ Error updating away team appearances for match ${match.awayTeamName}: ${error}`);
      }
    }

    console.log(`✅ Completed away team updates: ${awayUpdatedCount} matches processed`);

    // Step 5: Get summary statistics
    console.log('\n📊 Getting summary statistics...');
    
    const totalExpectedCleans = await sql`
      SELECT COUNT(*) as total_expected_cleans
      FROM appearances 
      WHERE expected_clean = true
    `;

    const expectedCleansByTeam = await sql`
      SELECT t.name as team_name, COUNT(*) as expected_cleans
      FROM appearances a
      JOIN teams t ON a.team_id = t.id
      WHERE a.expected_clean = true
      GROUP BY t.name
      ORDER BY expected_cleans DESC
    `;

    console.log(`\n📈 Summary:`);
    console.log(`  Total appearances with expected clean: ${totalExpectedCleans[0].total_expected_cleans}`);
    console.log(`  Home team matches processed: ${homeUpdatedCount}`);
    console.log(`  Away team matches processed: ${awayUpdatedCount}`);
    
    console.log('\n🏆 Expected cleans by team:');
    expectedCleansByTeam.slice(0, 10).forEach((team: any) => {
      console.log(`  ${team.team_name}: ${team.expected_cleans} expected cleans`);
    });

    // Verification: Show some sample updated records
    const sampleUpdates = await sql`
      SELECT p.name as player_name, t.name as team_name, a.minutes, a.started, a.expected_clean
      FROM appearances a
      JOIN players p ON a.player_id = p.id
      JOIN teams t ON a.team_id = t.id
      WHERE a.expected_clean = true
      LIMIT 10
    `;

    console.log('\n👥 Sample updated appearances:');
    sampleUpdates.forEach((app: any) => {
      console.log(`  ${app.player_name} (${app.team_name}): ${app.minutes}min, started: ${app.started}, expected_clean: ${app.expected_clean}`);
    });

  } catch (error) {
    console.error('❌ Error updating expected cleans:', error);
  } finally {
    await sql.end();
  }
}

updateExpectedCleans();
