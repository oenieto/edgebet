'use client';

import { X, CheckCircle2 } from 'lucide-react';
import type { Pick } from '@/types';
import { useUserStore } from '@/lib/store/userStore';

interface Props {
  pick: Pick;
  onClose: () => void;
}

export default function PickDetailModal({ pick, onClose }: Props) {
  const { bankroll } = useUserStore();
  const absoluteStake = (pick.suggestedStake / 100) * (Number(bankroll) || 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-surface border border-surface-container-low rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between p-4 border-b border-surface-container-low">
          <h2 className="font-sans font-bold text-lg text-on-surface">Detalle de Apuesta</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-surface-container-low text-tertiary hover:text-on-surface transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="text-[12px] text-tertiary uppercase tracking-widest font-semibold mb-1">
                {pick.league}
              </div>
              <div className="font-sans font-bold text-xl text-on-surface">
                {pick.homeTeam} vs {pick.awayTeam}
              </div>
            </div>
          </div>

          <div className="bg-surface-container-lowest border border-surface-container-low rounded-xl p-5 mb-6">
            <h3 className="font-sans font-bold text-[14px] text-on-surface mb-3 flex items-center gap-2">
              Recomendación del Modelo
            </h3>
            <p className="font-sans text-[14px] text-on-surface-variant leading-relaxed">
              {pick.aiReasoning || "El modelo detecta un patrón favorable basado en los datos históricos y la forma reciente."}
            </p>
          </div>

            {pick.combos && (
              <div className="bg-surface-container-lowest border border-surface-container-low rounded-xl p-5 mb-6">
                <h3 className="font-sans font-bold text-[14px] text-on-surface mb-3 flex items-center gap-2">
                  Construcción de Parlays
                </h3>
                <div className="space-y-3">
                  <div className="flex flex-col">
                    <span className="text-[11px] text-emerald-400 font-bold uppercase tracking-wider">Modo Seguro</span>
                    <span className="text-[13px] text-on-surface">{pick.combos.safe}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[11px] text-amber-400 font-bold uppercase tracking-wider">Modo Intermedio</span>
                    <span className="text-[13px] text-on-surface">{pick.combos.medium}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[11px] text-rose-400 font-bold uppercase tracking-wider">Modo Arriesgado</span>
                    <span className="text-[13px] text-on-surface">{pick.combos.risky}</span>
                  </div>
                </div>
              </div>
            )}

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-surface-container-lowest border border-surface-container-low rounded-xl p-4">
              <div className="text-[11px] text-tertiary uppercase tracking-widest font-semibold mb-1">
                Stake Sugerido
              </div>
              <div className="font-mono font-bold text-[20px] text-primary">
                ${absoluteStake.toFixed(2)}
              </div>
              <div className="text-[11px] text-tertiary mt-1">
                {pick.suggestedStake.toFixed(1)}% de tu bankroll
              </div>
            </div>
            
            <div className="bg-surface-container-lowest border border-surface-container-low rounded-xl p-4">
              <div className="text-[11px] text-tertiary uppercase tracking-widest font-semibold mb-1">
                Cuota (Odds)
              </div>
              <div className="font-mono font-bold text-[20px] text-on-surface">
                {pick.odds ? `@${pick.odds.toFixed(2)}` : 'N/A'}
              </div>
              <div className="text-[11px] text-tertiary mt-1">
                Cuota de referencia
              </div>
            </div>
          </div>
        </div>
        
        <div className="p-4 border-t border-surface-container-low bg-surface-container-lowest flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-full bg-primary text-on-primary font-sans font-bold text-[14px] hover:bg-primary/90 transition-colors"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}
