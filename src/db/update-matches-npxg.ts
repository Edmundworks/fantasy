import 'dotenv/config';
import { db } from './index';
import { matches } from './schema';
import { eq } from 'drizzle-orm';
import fs from 'fs';
import path from 'path';

interface MatchJson {
  home_team_npxg: string; // decimal as string
  away_team_npxg: string; // decimal as string
  home_team_name: string;
  away_team_name: string;
  match_id: string;
  match_url: string;
  gameweek?: number | null;
  processed_at?: number;
}

async function main(): Promise<void> {
  // Config
  const CLEAN_THRESHOLD = parseFloat(process.env.CLEAN_THRESHOLD || '0.7');

  // Load JSON
  const jsonPath = path.resolve(__dirname, '../../scraper/all_matches_npxg.json');
  const raw = fs.readFileSync(jsonPath, 'utf-8');
  const data = JSON.parse(raw) as Record<string, MatchJson>;

  let updatedCount = 0;
  let missingInDb = 0;
  let errors = 0;

  for (const [key, entry] of Object.entries(data)) {
    try {
      const homeNpxgNum = Number.parseFloat(entry.home_team_npxg);
      const awayNpxgNum = Number.parseFloat(entry.away_team_npxg);

      if (!Number.isFinite(homeNpxgNum) || !Number.isFinite(awayNpxgNum)) {
        // skip invalid
        continue;
      }

      const homeExpectedClean = awayNpxgNum <= CLEAN_THRESHOLD;
      const awayExpectedClean = homeNpxgNum <= CLEAN_THRESHOLD;

      const res = await db
        .update(matches)
        .set({
          homeTeamNonPenaltyExpectedGoals: entry.home_team_npxg,
          awayTeamNonPenaltyExpectedGoals: entry.away_team_npxg,
          homeTeamExpectedClean: homeExpectedClean,
          awayTeamExpectedClean: awayExpectedClean,
          updated_at: new Date(),
        })
        .where(eq(matches.matchReportUrl, entry.match_url))
        .returning({ id: matches.id });

      if (res.length === 0) {
        missingInDb += 1;
        // eslint-disable-next-line no-console
        console.warn(`Not found in DB for URL: ${entry.match_url}`);
      } else {
        updatedCount += 1;
      }
    } catch (err) {
      errors += 1;
      // eslint-disable-next-line no-console
      console.error(`Failed for ${entry.match_url}:`, err);
    }
  }

  // eslint-disable-next-line no-console
  console.log(`Done. Updated: ${updatedCount}, Missing in DB: ${missingInDb}, Errors: ${errors}`);
}

main().catch((e) => {
  // eslint-disable-next-line no-console
  console.error(e);
  process.exit(1);
});