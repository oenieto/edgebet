'use client';

import { Star } from 'lucide-react';

// TODO: add favorite_picks table and toggle button in pick detail page
export default function FavoritosPage() {
  return (
    <div className="max-w-[900px] mx-auto px-4 md:px-6 lg:px-8 py-10">
      <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-zinc-500 mb-4">Favoritos</div>
      <div className="rounded-xl border border-white/[0.06] bg-[#111114] p-10 text-center">
        <div className="w-12 h-12 rounded-full bg-white/[0.04] flex items-center justify-center mx-auto mb-4">
          <Star className="w-5 h-5 text-amber-300" />
        </div>
        <h1 className="font-sans text-lg font-bold text-white mb-1">Guarda tus picks favoritos para acceder rápido</h1>
        <p className="text-sm text-zinc-500">Aún no implementado — próximamente</p>
      </div>
    </div>
  );
}
