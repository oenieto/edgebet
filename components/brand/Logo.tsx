'use client';

import Image from 'next/image';
import Link from 'next/link';

type Variant = 'horizontal' | 'vertical' | 'mark';
type Theme = 'light' | 'dark';

interface LogoProps {
  variant?: Variant;
  theme?: Theme;
  height?: number;
  href?: string | null;
  className?: string;
  priority?: boolean;
}

const SOURCES: Record<Variant, Record<Theme, string>> = {
  horizontal: { light: '/logo.png', dark: '/inverso.png' },
  vertical:   { light: '/logovertical.png', dark: '/logovertical.png' },
  mark:       { light: '/favicon.png', dark: '/favicon.png' },
};

const RATIOS: Record<Variant, number> = {
  horizontal: 4,
  vertical: 1,
  mark: 1,
};

export default function Logo({
  variant = 'horizontal',
  theme = 'dark',
  height = 48,
  href = '/dashboard',
  className,
  priority,
}: LogoProps) {
  const src = SOURCES[variant][theme];
  const width = Math.round(height * RATIOS[variant]);

  const img = (
    <Image
      src={src}
      alt="Edgebet"
      width={width}
      height={height}
      priority={priority}
      className={`h-[${height}px] w-auto select-none object-cover object-top ${className ?? ''}`}
      style={{ height: `${height}px`, width: 'auto', clipPath: 'inset(0 0 12% 0)' }}
    />
  );

  if (href === null) return img;
  return (
    <Link href={href} className="inline-flex items-center shrink-0">
      {img}
    </Link>
  );
}
