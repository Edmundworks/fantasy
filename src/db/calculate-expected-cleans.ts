import 'dotenv/config';
import { db } from './index';
import { matches, teams } from './schema';
import { eq, and } from 'drizzle-orm';
import { writeFileSync } from 'fs';
import { join } from 'path';

interface TeamExpectedCleans {
  teamName: string;
  teamId: string;
  totalExpectedCleans: number;
}

async function main(): Promise<void> {
  // Get all teams
  const allTeams = await db.select().from(teams);
  console.log(`Found ${allTeams.length} teams`);

  const results: TeamExpectedCleans[] = [];

  for (const team of allTeams) {
    // Count home expected cleans (where this team is home and homeTeamExpectedClean is true)
    const homeCleans = await db
      .select()
      .from(matches)
      .where(and(
        eq(matches.homeTeamId, team.id),
        eq(matches.homeTeamExpectedClean, true)
      ));

    // Count away expected cleans (where this team is away and awayTeamExpectedClean is true)
    const awayCleans = await db
      .select()
      .from(matches)
      .where(and(
        eq(matches.awayTeamId, team.id),
        eq(matches.awayTeamExpectedClean, true)
      ));

    const totalExpectedCleans = homeCleans.length + awayCleans.length;

    results.push({
      teamName: team.name,
      teamId: team.id,
      totalExpectedCleans
    });

    console.log(`${team.name}: ${homeCleans.length} home + ${awayCleans.length} away = ${totalExpectedCleans} total`);
  }

  // Sort by total expected cleans descending
  results.sort((a, b) => b.totalExpectedCleans - a.totalExpectedCleans);

  // Save to JSON file
  const outputPath = join(__dirname, 'expected_cleans.json');
  writeFileSync(outputPath, JSON.stringify(results, null, 2));

  console.log(`\nSaved results to ${outputPath}`);
  console.log(`Total teams: ${results.length}`);
  console.log(`Total expected cleans across all teams: ${results.reduce((sum, team) => sum + team.totalExpectedCleans, 0)}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});