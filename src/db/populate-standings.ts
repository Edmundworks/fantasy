import 'dotenv/config';
import { db } from './index';
import { seasons, standings } from './schema';
import { and, eq } from 'drizzle-orm';
import { readFileSync } from 'fs';
import { join } from 'path';

interface TeamExpectedCleans {
  teamName: string;
  teamId: string;
  totalExpectedCleans: number;
}

async function main(): Promise<void> {
  const TARGET_SEASON = '2024-2025';

  // Find season row
  const seasonRows = await db.select().from(seasons).where(eq(seasons.season, TARGET_SEASON));
  if (seasonRows.length === 0) {
    throw new Error(`Season not found: ${TARGET_SEASON}`);
  }
  const seasonRow = seasonRows[0];

  // Load expected cleans data from JSON
  const jsonPath = join(__dirname, 'expected_cleans.json');
  const expectedCleansData: TeamExpectedCleans[] = JSON.parse(readFileSync(jsonPath, 'utf8'));

  console.log(`Loading data for ${expectedCleansData.length} teams from expected_cleans.json`);

  // For each team in the JSON data, insert/update standings
  let inserted = 0;
  for (const teamData of expectedCleansData) {
    // Upsert-like behavior: try delete existing row for (seasonId, teamId) then insert
    await db.delete(standings).where(and(eq(standings.seasonId, seasonRow.id), eq(standings.teamId, teamData.teamId)));

    await db.insert(standings).values({
      seasonId: seasonRow.id,
      season: TARGET_SEASON,
      teamId: teamData.teamId,
      teamName: teamData.teamName,
      expectedCleans: teamData.totalExpectedCleans,
    });

    console.log(`${teamData.teamName}: ${teamData.totalExpectedCleans} expected cleans`);
    inserted += 1;
  }

  // eslint-disable-next-line no-console
  console.log(`\nStandings populated for ${TARGET_SEASON}. Rows: ${inserted}`);
}

main().catch((e) => {
  // eslint-disable-next-line no-console
  console.error(e);
  process.exit(1);
});