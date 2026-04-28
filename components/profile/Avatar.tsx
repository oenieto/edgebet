'use client';

import { avatarById, type PresetAvatar } from '@/lib/ranking/avatars';

interface AvatarProps {
  presetId?: string | null;
  customDataUrl?: string | null;
  initials?: string;
  size?: number;
  ringColor?: string;
  className?: string;
}

export default function Avatar({
  presetId,
  customDataUrl,
  initials = '',
  size = 56,
  ringColor,
  className,
}: AvatarProps) {
  const styleSize = { width: size, height: size };

  if (customDataUrl) {
    return (
      <div
        className={`rounded-full overflow-hidden ${ringColor ? 'ring-2' : ''} ${className ?? ''}`}
        style={{ ...styleSize, boxShadow: ringColor ? `0 0 0 2px ${ringColor}` : undefined }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={customDataUrl} alt="Avatar" width={size} height={size} className="w-full h-full object-cover" />
      </div>
    );
  }

  const preset = avatarById(presetId ?? 'of-red');
  return (
    <div
      className={`rounded-full overflow-hidden ${className ?? ''}`}
      style={{ ...styleSize, boxShadow: ringColor ? `0 0 0 2px ${ringColor}` : undefined }}
    >
      {preset.imageUrl ? (
        <img src={preset.imageUrl} alt={preset.label} width={size} height={size} className="w-full h-full object-cover" />
      ) : (
        <PresetSvg preset={preset} size={size} initials={initials} />
      )}
    </div>
  );
}

export function PresetSvg({
  preset,
  size = 56,
  initials = '',
}: {
  preset: PresetAvatar;
  size?: number;
  initials?: string;
}) {
  const [c1, c2] = preset.gradient || ['#111', '#222'];
  const id = `g-${preset.id}`;
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={c1} />
          <stop offset="100%" stopColor={c2} />
        </linearGradient>
      </defs>
      <rect width="100" height="100" fill={`url(#${id})`} />
      <Pattern kind={preset.pattern} />
      {initials && (
        <text
          x="50"
          y="56"
          textAnchor="middle"
          fontFamily="ui-sans-serif, system-ui"
          fontSize="34"
          fontWeight="800"
          fill="rgba(255,255,255,0.95)"
          dominantBaseline="middle"
        >
          {initials.slice(0, 2).toUpperCase()}
        </text>
      )}
    </svg>
  );
}

function Pattern({ kind }: { kind: PresetAvatar['pattern'] }) {
  const stroke = 'rgba(255,255,255,0.18)';
  switch (kind) {
    case 'rings':
      return (
        <g fill="none" stroke={stroke} strokeWidth="2">
          <circle cx="50" cy="50" r="32" />
          <circle cx="50" cy="50" r="44" />
        </g>
      );
    case 'arc':
      return (
        <path d="M10 78 Q 50 30 90 78" fill="none" stroke={stroke} strokeWidth="3" />
      );
    case 'wave':
      return (
        <path d="M0 60 Q 25 40 50 60 T 100 60" fill="none" stroke={stroke} strokeWidth="3" />
      );
    case 'dot':
      return (
        <g fill={stroke}>
          <circle cx="22" cy="22" r="3" />
          <circle cx="78" cy="22" r="3" />
          <circle cx="22" cy="78" r="3" />
          <circle cx="78" cy="78" r="3" />
        </g>
      );
    case 'cross':
      return (
        <g stroke={stroke} strokeWidth="2">
          <line x1="20" y1="20" x2="80" y2="80" />
          <line x1="80" y1="20" x2="20" y2="80" />
        </g>
      );
    case 'star':
      return (
        <polygon
          points="50,18 56,40 80,40 60,54 68,76 50,62 32,76 40,54 20,40 44,40"
          fill={stroke}
        />
      );
    case 'spark':
      return (
        <g fill={stroke}>
          <polygon points="50,12 54,46 88,50 54,54 50,88 46,54 12,50 46,46" />
        </g>
      );
    case 'shield':
      return (
        <path
          d="M50 14 L80 26 L80 56 Q 80 78 50 86 Q 20 78 20 56 L20 26 Z"
          fill="none"
          stroke={stroke}
          strokeWidth="2"
        />
      );
  }
}
