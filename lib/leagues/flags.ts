export interface LeagueFlag {
  flag: string;
  country: string;
  shortName: string;
}

const BY_SLUG: Record<string, LeagueFlag> = {
  'premier-league':   { flag: '🇬🇧', country: 'Inglaterra', shortName: 'Premier' },
  'la-liga':          { flag: '🇪🇸', country: 'España',     shortName: 'La Liga' },
  'bundesliga':       { flag: '🇩🇪', country: 'Alemania',   shortName: 'Bundesliga' },
  'serie-a':          { flag: '🇮🇹', country: 'Italia',     shortName: 'Serie A' },
  'ligue-1':          { flag: '🇫🇷', country: 'Francia',    shortName: 'Ligue 1' },
  'eredivisie':       { flag: '🇳🇱', country: 'Países Bajos', shortName: 'Eredivisie' },
  'primeira-liga':    { flag: '🇵🇹', country: 'Portugal',   shortName: 'Primeira' },
  'liga-mx':          { flag: '🇲🇽', country: 'México',     shortName: 'Liga MX' },
  'mls':              { flag: '🇺🇸', country: 'EE.UU.',     shortName: 'MLS' },
  'brasileirao':      { flag: '🇧🇷', country: 'Brasil',     shortName: 'Brasileirão' },
  'champions-league': { flag: '🇪🇺', country: 'Europa',     shortName: 'Champions' },
  'europa-league':    { flag: '🇪🇺', country: 'Europa',     shortName: 'Europa L.' },
  'copa-libertadores':{ flag: '🌎', country: 'Sudamérica',  shortName: 'Libertadores' },
};

const FALLBACK: LeagueFlag = { flag: '⚐', country: '—', shortName: '—' };

export function flagForLeague(slug?: string | null): LeagueFlag {
  if (!slug) return FALLBACK;
  return BY_SLUG[slug] ?? FALLBACK;
}
