import { db } from './index.js';
import { players } from './schema.js';
import { eq } from 'drizzle-orm';
import * as fs from 'fs';
import * as path from 'path';

// Element type mapping from CSV to our position codes
const ELEMENT_TYPE_MAP: Record<string, string> = {
  'GK': 'GK',   // Goalkeeper
  'DEF': 'DEF', // Defender  
  'MID': 'MID', // Midfielder
  'FWD': 'FWD'  // Forward
};

interface FPLPlayer {
  first_name: string;
  second_name: string;
  element_type: string;
  now_cost: string;
}

function convertPrice(nowCost: string): number {
  // Convert FPL price format (40 = 4.0, 45 = 4.5, 100 = 10.0, etc.)
  const cost = parseInt(nowCost);
  return cost / 10.0;
}

function normalizePlayerName(firstName: string, lastName: string): string {
  // Create full name similar to how our data might be formatted
  return `${firstName} ${lastName}`.trim();
}

function createNameVariations(firstName: string, lastName: string): string[] {
  // Create various name combinations to match against
  const variations = [
    `${firstName} ${lastName}`,
    `${firstName.split(' ')[0]} ${lastName}`, // Use first part of first name
    lastName, // Just last name
    firstName, // Just first name (for cases like "Gabriel")
    `${firstName} ${lastName.split(' ')[0]}`, // First name + first part of last name
    `${firstName.split(' ')[0]} ${lastName.split(' ')[0]}`, // First part of each name
    firstName.split(' ')[0], // Just first part of first name
    lastName.split(' ')[0], // Just first part of last name
  ];
  
  // Remove duplicates and empty strings, and filter out very short names
  return [...new Set(variations.filter(name => name.trim().length > 2))];
}

async function updateFPLData() {
  try {
    console.log('📊 Reading FPL data from CSV...');
    
    // Read and parse CSV file
    const csvPath = path.join(process.cwd(), 'fpl_players_2025-26.csv');
    const csvContent = fs.readFileSync(csvPath, 'utf-8');
    const lines = csvContent.split('\n').filter(line => line.trim());
    
    // Parse header - join all lines until we have all columns, then clean it
    let headerLine = lines[0];
    for (let i = 1; i < lines.length; i++) {
      if (headerLine.includes('element_type')) break;
      headerLine += lines[i];
    }
    
    // Clean the header and split by comma
    const cleanHeader = headerLine.replace(/\n/g, '').replace(/\r/g, '');
    const header = cleanHeader.split(',').map(col => col.trim());
    
    console.log('📊 CSV columns found:', header);
    
    const firstNameIdx = header.indexOf('first_name');
    const secondNameIdx = header.indexOf('second_name');
    const elementTypeIdx = header.indexOf('element_type');
    const nowCostIdx = header.indexOf('now_cost');
    
    if (firstNameIdx === -1 || secondNameIdx === -1 || elementTypeIdx === -1 || nowCostIdx === -1) {
      throw new Error('Required columns not found in CSV');
    }
    
    // Parse FPL players - start from line that contains actual data
    const fplPlayers: FPLPlayer[] = [];
    let dataStartIndex = 1;
    
    // Find where actual data starts (skip header lines)
    for (let i = 1; i < lines.length; i++) {
      if (lines[i].includes(',') && !lines[i].includes('first_name')) {
        dataStartIndex = i;
        break;
      }
    }
    
    for (let i = dataStartIndex; i < lines.length; i++) {
      const cells = lines[i].split(',');
      if (cells.length >= Math.max(firstNameIdx, secondNameIdx, elementTypeIdx, nowCostIdx) + 1) {
        const firstName = cells[firstNameIdx]?.trim() || '';
        const secondName = cells[secondNameIdx]?.trim() || '';
        const elementType = cells[elementTypeIdx]?.trim() || '';
        const nowCost = cells[nowCostIdx]?.trim() || '';
        
        if (firstName && secondName && elementType && nowCost) {
          fplPlayers.push({
            first_name: firstName,
            second_name: secondName,
            element_type: elementType,
            now_cost: nowCost
          });
        }
      }
    }
    
    console.log(`📊 Parsed ${fplPlayers.length} FPL players from CSV`);
    
    // Get all players from database
    console.log('🔍 Fetching players from database...');
    const dbPlayers = await db.select().from(players);
    console.log(`🔍 Found ${dbPlayers.length} players in database`);
    
    let matchCount = 0;
    let updateCount = 0;
    const unmatched: string[] = [];
    
    console.log('🔄 Matching FPL data to database players...');
    
    for (const fplPlayer of fplPlayers) {
      if (!fplPlayer.first_name || !fplPlayer.second_name) continue;
      
      const nameVariations = createNameVariations(fplPlayer.first_name, fplPlayer.second_name);
      let matchFound = false;
      
      for (const dbPlayer of dbPlayers) {
        // Try to match against name variations
        const dbPlayerName = dbPlayer.name.toLowerCase().trim();
        
        for (const variation of nameVariations) {
          const variationLower = variation.toLowerCase().trim();
          
          // Exact match or contains match
          if (dbPlayerName === variationLower || 
              dbPlayerName.includes(variationLower) ||
              variationLower.includes(dbPlayerName) ||
              // For single names like "Gabriel", check if it's the main part of the full name
              (variation.length > 3 && dbPlayerName.split(' ')[0] === variationLower) ||
              (variation.length > 3 && dbPlayerName.split(' ').includes(variationLower))) {
            
            matchFound = true;
            matchCount++;
            
            const price = convertPrice(fplPlayer.now_cost);
            const position = ELEMENT_TYPE_MAP[fplPlayer.element_type] || fplPlayer.element_type;
            
            console.log(`✅ Match: "${dbPlayer.name}" ↔ "${fplPlayer.first_name} ${fplPlayer.second_name}" (${position}, £${price}m)`);
            
            // Update the player
            await db.update(players)
              .set({
                fplPosition: position,
                price: price.toString(),
                updated_at: new Date()
              })
              .where(eq(players.id, dbPlayer.id));
            
            updateCount++;
            break;
          }
        }
        
        if (matchFound) break;
      }
      
      if (!matchFound) {
        unmatched.push(`${fplPlayer.first_name} ${fplPlayer.second_name} (${fplPlayer.element_type})`);
      }
    }
    
    console.log('\\n📊 Summary:');
    console.log(`✅ Total matches found: ${matchCount}`);
    console.log(`🔄 Players updated: ${updateCount}`);
    console.log(`❌ Unmatched FPL players: ${unmatched.length}`);
    
    if (unmatched.length > 0) {
      console.log('\\n❌ Unmatched FPL players:');
      unmatched.slice(0, 10).forEach(name => console.log(`   • ${name}`));
      if (unmatched.length > 10) {
        console.log(`   ... and ${unmatched.length - 10} more`);
      }
    }
    
    console.log('\\n🎉 FPL data update completed!');
    
  } catch (error) {
    console.error('❌ Error updating FPL data:', error);
    process.exit(1);
  }
}

updateFPLData();
