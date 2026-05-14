'use client';

import { motion } from 'framer-motion';
import { Compass, Sparkles, Telescope } from 'lucide-react';
import Link from 'next/link';

type Variant = 'searching' | 'no-results' | 'error';

interface Props {
  variant?: Variant;
  title?: string;
  description?: string;
  ctaHref?: string;
  ctaLabel?: string;
}

const COPY: Record<Variant, { title: string; description: string; icon: React.ReactNode; tone: string }> = {
  searching: {
    title: 'Buscando las mejores oportunidades…',
    description:
      'El motor está cruzando el modelo ML con Polymarket y Bet365 para detectar divergencias con edge real.',
    icon: <Telescope className="w-6 h-6" />,
    tone: 'from-indigo-500/15 via-indigo-500/5 to-transparent border-indigo-500/20 text-indigo-300',
  },
  'no-results': {
    title: 'No hay picks para este filtro',
    description:
      'Prueba con otra liga o quita el filtro de búsqueda. Cuando hay edge confirmado, aparece aquí en menos de un minuto.',
    icon: <Compass className="w-6 h-6" />,
    tone: 'from-white/[0.06] via-white/[0.02] to-transparent border-white/[0.08] text-zinc-300',
  },
  error: {
    title: 'Backend no disponible',
    description:
      'No pudimos conectar con FastAPI. Asegúrate de tenerlo corriendo en :8000 y vuelve a cargar la página.',
    icon: <Sparkles className="w-6 h-6" />,
    tone: 'from-red-500/15 via-red-500/5 to-transparent border-red-500/30 text-red-300',
  },
};

export default function PicksEmptyState({
  variant = 'no-results',
  title,
  description,
  ctaHref,
  ctaLabel,
}: Props) {
  const cfg = COPY[variant];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className={`relative overflow-hidden bg-gradient-to-br ${cfg.tone} border rounded-xl p-8 md:p-10 flex flex-col items-center text-center`}
    >
      {/* Halo animado de fondo — sutil */}
      <motion.div
        aria-hidden
        initial={{ opacity: 0.0, scale: 0.8 }}
        animate={{ opacity: [0.15, 0.35, 0.15], scale: [0.9, 1.1, 0.9] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute -top-20 left-1/2 -translate-x-1/2 w-64 h-64 rounded-full bg-current blur-3xl pointer-events-none"
      />

      <motion.div
        initial={{ scale: 0.85, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="relative w-14 h-14 rounded-2xl bg-white/[0.06] border border-white/[0.08] flex items-center justify-center mb-4"
      >
        {cfg.icon}
        {variant === 'searching' && (
          <motion.span
            aria-hidden
            className="absolute inset-0 rounded-2xl border border-current"
            initial={{ opacity: 0.5, scale: 1 }}
            animate={{ opacity: 0, scale: 1.4 }}
            transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut' }}
          />
        )}
      </motion.div>

      <h3 className="font-sans font-bold text-[15px] md:text-[16px] text-white tracking-tight mb-1.5 max-w-md">
        {title ?? cfg.title}
      </h3>
      <p className="font-sans text-[12.5px] text-zinc-400 max-w-md leading-relaxed">
        {description ?? cfg.description}
      </p>

      {ctaHref && ctaLabel && (
        <Link
          href={ctaHref}
          className="mt-5 inline-flex items-center h-[34px] px-4 rounded-md bg-white text-[#0a0a0c] font-sans font-bold text-[12px] hover:bg-zinc-200 transition-colors"
        >
          {ctaLabel}
        </Link>
      )}
    </motion.div>
  );
}
