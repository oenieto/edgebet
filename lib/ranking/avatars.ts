export interface PresetAvatar {
  id: string;
  label: string;
  imageUrl?: string;
  gradient?: [string, string];
  pattern?: 'rings' | 'arc' | 'dot' | 'wave' | 'cross' | 'star' | 'spark' | 'shield';
}

export const PRESET_AVATARS: PresetAvatar[] = [
  { id: 'of-red', label: 'OneFootball Rojo', imageUrl: '/avatars/avatar_red_1777355662718.png' },
  { id: 'of-blue', label: 'OneFootball Azul', imageUrl: '/avatars/avatar_blue_1777355677720.png' },
  { id: 'of-green', label: 'OneFootball Verde', imageUrl: '/avatars/avatar_green_1777355690699.png' },
  { id: 'of-yellow', label: 'OneFootball Amarillo', imageUrl: '/avatars/avatar_yellow_1777355703426.png' },
  { id: 'edge-1',  label: 'Edge',     gradient: ['#6366f1', '#8b5cf6'], pattern: 'rings' },
  { id: 'flame-1', label: 'Flama',    gradient: ['#f97316', '#f43f5e'], pattern: 'arc' },
  { id: 'cool-1',  label: 'Frost',    gradient: ['#06b6d4', '#3b82f6'], pattern: 'wave' },
  { id: 'gold-1',  label: 'Oro',      gradient: ['#fbbf24', '#f59e0b'], pattern: 'star' },
];

export const DEFAULT_AVATAR_ID = 'of-red';

export function avatarById(id: string): PresetAvatar {
  return PRESET_AVATARS.find((a) => a.id === id) ?? PRESET_AVATARS[0];
}
