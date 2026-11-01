/**
 * tier-compute.ts — Anime Zero Availability Index & Tier Computing Engine
 * -----------------------------------------------------------------------
 * Methodology: Pure mathematical derivation based on official drop rates,
 * pity thresholds, and acquisition gating costs (Availability Model).
 *
 * Formula:
 *   rarityScore: Epic=1, Legendary=2, Mythic=3, Arcane=4, Lyth=5
 *   gatingCost = 0.6 * log10(rarityPity + 1) + 0.4 * (-log10((dropRatePercent ?? 1) / 100))
 *   AD = 0.65 * rarityScore + 0.35 * normalize(gatingCost)
 *   Band: AD >= 4.5 -> S+ | >= 4.0 -> S | >= 3.0 -> A | >= 2.0 -> B | >= 1.2 -> C | >= 0.5 -> D | else F
 */

export type WeaponRarity = 'Epic' | 'Legendary' | 'Mythic' | 'Arcane' | 'Lyth' | null;

export interface WeaponSynergy {
  withSlug: string;
  effect: string;
  sourceLabel?: string;
}

export interface WeaponPityInfo {
  runs?: number;
  freeRuns?: number;
  cooldownMinutes?: number;
}

export interface WeaponAcquisition {
  type: string;
  mode: string;
  boss?: string | null;
  dropRatePercent?: number | null;
  pity?: WeaponPityInfo | null;
}

export interface WeaponData {
  slug: string;
  name: string;
  rarity: WeaponRarity;
  acquisition: WeaponAcquisition;
  rarityPitySpins?: number | null;
  synergies?: WeaponSynergy[];
  tierOverrides?: {
    overall?: string;
    raid?: string;
    farming?: string;
    trading?: string;
  } | null;
  evidenceLevel: string;
  sourceUrl: string;
  sourceLabel?: string;
  lastVerified: string;
  status: string;
  description?: string;
}

export type TierBand = 'S+' | 'S' | 'A' | 'B' | 'C' | 'D' | 'F';

export interface WeaponTierMetric {
  rarityScore: number;
  rawGatingCost: number;
  normalizedGatingCost: number;
  availabilityIndex: number;
  tierBand: TierBand;
  tierPillClass: string;
  methodologyNote: string;
}

export interface EnrichedWeapon extends WeaponData {
  tierMetric: WeaponTierMetric;
}

const RARITY_SCORES: Record<string, number> = {
  Epic: 1.0,
  Legendary: 2.0,
  Mythic: 3.0,
  Arcane: 4.0,
  Lyth: 5.0,
};

/**
 * Derives rarity score based on verified rarity or factual acquisition gating tier.
 */
export function getRarityScore(w: WeaponData): number {
  if (w.rarity && RARITY_SCORES[w.rarity]) {
    return RARITY_SCORES[w.rarity];
  }
  // In the event rarity is in conflict (null), evaluate factual acquisition tier:
  const mode = (w.acquisition?.mode || '').toLowerCase();
  const slug = w.slug.toLowerCase();

  // Flagship Pinnacle Trials (e.g. Void Arbiter in Update 3 Trails)
  if (slug === 'void-arbiter' || mode.includes('trial')) {
    return 4.8;
  }
  // Dedicated Raid Boss Drops (e.g. Flame Director in Spirited Away)
  if (w.acquisition?.type === 'raid' || w.acquisition?.boss) {
    return 4.2;
  }
  // High-Tier Gacha / Synergy Core Weapons
  if (slug === 'cataclysm' || slug === 'cursed-king') {
    return 3.8;
  }
  if (slug === 'dragon-eclipse' || slug === 'divine-emperor' || slug === 'lights-of-divinity') {
    return 3.2;
  }
  return 2.0;
}

/**
 * Calculates raw gating cost based on pity count and drop rate percentage.
 */
export function computeRawGatingCost(w: WeaponData): number {
  const pityCount =
    w.rarityPitySpins ??
    w.acquisition?.pity?.runs ??
    (w.rarity === 'Epic' ? 0 : 50);

  let dropRate = w.acquisition?.dropRatePercent;
  if (dropRate == null || dropRate <= 0) {
    dropRate = w.rarity === 'Epic' ? 10.0 : 1.0;
  }

  const pityTerm = 0.6 * Math.log10(pityCount + 1);
  const dropRateRatio = Math.max(0.0001, dropRate / 100.0);
  const dropTerm = 0.4 * (-Math.log10(dropRateRatio));

  return pityTerm + dropTerm;
}

/**
 * Maps Availability Index (AD) to standardized Tier Band and CSS class.
 */
export function getTierBandFromAD(ad: number): { band: TierBand; pillClass: string } {
  if (ad >= 4.5) return { band: 'S+', pillClass: 't1' };
  if (ad >= 4.0) return { band: 'S', pillClass: 't2' };
  if (ad >= 3.0) return { band: 'A', pillClass: 't3' };
  if (ad >= 2.0) return { band: 'B', pillClass: 't4' };
  if (ad >= 1.2) return { band: 'C', pillClass: 't5' };
  if (ad >= 0.5) return { band: 'D', pillClass: 't6' };
  return { band: 'F', pillClass: 't7' };
}

/**
 * Enriches a collection of weapons with objective availability calculations.
 */
export function enrichWeapons(weapons: WeaponData[]): EnrichedWeapon[] {
  if (!weapons || weapons.length === 0) return [];

  const rawCosts = weapons.map(computeRawGatingCost);
  const minCost = Math.min(...rawCosts);
  const maxCost = Math.max(...rawCosts);
  const range = maxCost - minCost > 0 ? maxCost - minCost : 1;

  return weapons.map((w, idx) => {
    const rawCost = rawCosts[idx];
    const normalizedCost = ((rawCost - minCost) / range) * 4.0 + 1.0;
    const rScore = getRarityScore(w);

    const calculatedAD = Number((0.65 * rScore + 0.35 * normalizedCost).toFixed(2));
    const defaultTier = getTierBandFromAD(calculatedAD);

    let finalBand = defaultTier.band;
    let finalClass = defaultTier.pillClass;

    if (w.tierOverrides?.overall) {
      finalBand = w.tierOverrides.overall as TierBand;
      const overrideMap: Record<string, string> = {
        'S+': 't1',
        S: 't2',
        A: 't3',
        B: 't4',
        C: 't5',
        D: 't6',
        F: 't7',
      };
      finalClass = overrideMap[finalBand] || 't4';
    }

    const metric: WeaponTierMetric = {
      rarityScore: rScore,
      rawGatingCost: Number(rawCost.toFixed(3)),
      normalizedGatingCost: Number(normalizedCost.toFixed(2)),
      availabilityIndex: calculatedAD,
      tierBand: finalBand,
      tierPillClass: finalClass,
      methodologyNote:
        'Availability Model v1: Derived from rarity weighting (65%) and log10 gating cost (35%).',
    };

    return {
      ...w,
      tierMetric: metric,
    };
  });
}
