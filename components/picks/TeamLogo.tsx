'use client';

import { useState } from 'react';

interface TeamLogoProps {
  src?: string | null;
  name: string;
  size?: number;
  className?: string;
}

function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join('');
}

export default function TeamLogo({ src, name, size = 48, className = '' }: TeamLogoProps) {
  const [errored, setErrored] = useState(false);
  const showFallback = !src || errored;

  if (showFallback) {
    return (
      <div
        className={`shrink-0 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center font-mono font-bold text-zinc-300 ${className}`}
        style={{ width: size, height: size, fontSize: Math.max(10, Math.round(size * 0.32)) }}
        aria-label={name}
      >
        {initials(name) || '·'}
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={name}
      width={size}
      height={size}
      onError={() => setErrored(true)}
      className={`shrink-0 object-contain ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
