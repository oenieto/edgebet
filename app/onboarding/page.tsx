'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { apiFetch } from '@/lib/api/client';
import { Shield, Scale, Zap, Loader2, Minus, Plus } from 'lucide-react';
import { useUserStore } from '@/lib/store/userStore';

const LEAGUES = [
  { code: 'E0', name: 'Premier League', flag: '🏴󠁧󠁢󠁥󠁮󠁧󠁿' },
  { code: 'SP1', name: 'La Liga', flag: '🇪🇸' },
  { code: 'D1', name: 'Bundesliga', flag: '🇩🇪' },
  { code: 'I1', name: 'Serie A', flag: '🇮🇹' },
  { code: 'F1', name: 'Ligue 1', flag: '🇫🇷' },
  { code: 'UCL', name: 'Champions', flag: '🏆' },
  { code: 'N1', name: 'Eredivisie', flag: '🇳🇱' },
  { code: 'MX1', name: 'Liga MX', flag: '🇲🇽' },
];

export default function Onboarding() {
  const { user, token } = useAuth();
  const store = useUserStore();
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);

  const [profile, setProfile] = useState<'conservative' | 'balanced' | 'aggressive' | null>(null);
  const [bankroll, setBankroll] = useState(1000);
  const [favorites, setFavorites] = useState<string[]>([]);

  const toggleLeague = (code: string) => {
    setFavorites((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code],
    );
  };

  const handleFinish = async () => {
    const currentToken = token || window.localStorage.getItem('edgebet.auth.token');
    if (!user || !currentToken) return;
    setLoading(true);
    try {
      await apiFetch(`/user/${user.id}/profile`, {
        method: 'POST',
        token: currentToken,
        body: {
          risk_profile: profile,
          bankroll,
          horizon: '1mes',
          favorite_leagues: favorites,
        },
      });
      store.completeOnboarding();
      if (user) {
        const updatedUser = { ...user, onboarding_done: true };
        window.localStorage.setItem('edgebet.auth.user', JSON.stringify(updatedUser));
      }
      router.push('/dashboard');
    } catch (e) {
      console.error(e);
      alert('Error guardando perfil. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-2xl bg-[#111114] border border-white/[0.06] rounded-2xl p-8 relative overflow-hidden">
        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full ${
                step >= i ? 'bg-amber-500' : 'bg-white/10'
              }`}
            />
          ))}
        </div>

        {step === 1 && (
          <div className="animate-in fade-in slide-in-from-bottom-4">
            <h1 className="text-2xl font-bold font-sans tracking-tight mb-2">
              ¿Cómo prefieres apostar?
            </h1>
            <p className="text-zinc-400 mb-8 text-sm">
              Define tu perfil de riesgo para personalizar las recomendaciones de stakes y picks.
            </p>

            <div className="grid gap-4">
              <button
                onClick={() => setProfile('conservative')}
                className={`p-5 rounded-xl border text-left transition-colors flex gap-4 items-start ${
                  profile === 'conservative'
                    ? 'border-amber-500 bg-amber-500/10'
                    : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                }`}
              >
                <div className="mt-1 w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base mb-1">Seguro</h3>
                  <p className="text-sm text-zinc-400 leading-relaxed">
                    Picks +68% confianza, 3% del bankroll por pick. Crecimiento lento y constante.
                  </p>
                </div>
              </button>

              <button
                onClick={() => setProfile('balanced')}
                className={`p-5 rounded-xl border text-left transition-colors flex gap-4 items-start relative ${
                  profile === 'balanced'
                    ? 'border-amber-500 bg-amber-500/10'
                    : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                }`}
              >
                <div className="absolute -top-3 right-4 px-2 py-0.5 bg-amber-500 text-black text-[10px] font-bold uppercase tracking-widest rounded-full">
                  Recomendado
                </div>
                <div className="mt-1 w-10 h-10 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
                  <Scale className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base mb-1">Equilibrado</h3>
                  <p className="text-sm text-zinc-400 leading-relaxed">
                    Picks +60% confianza, 5% del bankroll por pick. El mejor balance riesgo/retorno.
                  </p>
                </div>
              </button>

              <button
                onClick={() => setProfile('aggressive')}
                className={`p-5 rounded-xl border text-left transition-colors flex gap-4 items-start ${
                  profile === 'aggressive'
                    ? 'border-amber-500 bg-amber-500/10'
                    : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                }`}
              >
                <div className="mt-1 w-10 h-10 rounded-full bg-red-500/20 text-red-400 flex items-center justify-center shrink-0">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base mb-1">Arriesgado</h3>
                  <p className="text-sm text-zinc-400 leading-relaxed">
                    Todos los picks incluyendo valor, 10% del bankroll por pick. Mayor retorno potencial.
                  </p>
                </div>
              </button>
            </div>

            <div className="mt-8 flex justify-end">
              <button
                disabled={!profile}
                onClick={() => setStep(2)}
                className="px-6 py-2.5 bg-white text-black font-semibold rounded-lg disabled:opacity-50 transition-opacity"
              >
                Continuar
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="animate-in fade-in slide-in-from-right-8">
            <h1 className="text-2xl font-bold font-sans tracking-tight mb-2">
              ¿Cuánto tienes disponible para apostar?
            </h1>
            <p className="text-zinc-400 mb-8 text-sm">
              Tu bankroll solo lo usamos para calcular tus planes. No se comparte con nadie.
            </p>

            <div className="mb-10 text-center">
              <div className="inline-flex items-center gap-4 bg-white/5 border border-white/10 rounded-2xl p-2 px-4 shadow-inner mb-8">
                <button
                  onClick={() => setBankroll((prev) => Math.max(50, prev - 100))}
                  className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors border border-white/5"
                >
                  <Minus className="w-5 h-5 text-zinc-400" />
                </button>
                <div className="flex items-center justify-center font-mono font-bold text-white min-w-[140px]">
                  <span className="text-zinc-500 mr-1 text-4xl">$</span>
                  <input
                    type="number"
                    value={bankroll}
                    onChange={(e) => setBankroll(Number(e.target.value))}
                    className="bg-transparent outline-none w-full text-center text-5xl [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                  />
                </div>
                <button
                  onClick={() => setBankroll((prev) => Math.min(50000, prev + 100))}
                  className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors border border-white/5"
                >
                  <Plus className="w-5 h-5 text-zinc-400" />
                </button>
              </div>

              <input
                type="range"
                min="50"
                max="50000"
                step="50"
                value={bankroll}
                onChange={(e) => setBankroll(Number(e.target.value))}
                className="w-full accent-amber-500 mb-6"
              />

              <div className="flex flex-wrap justify-center gap-2 mb-8">
                {[500, 1000, 5000, 10000].map((val) => (
                  <button
                    key={val}
                    onClick={() => setBankroll(val)}
                    className="px-4 py-1.5 rounded-full border border-white/10 hover:bg-white/5 font-mono text-sm"
                  >
                    ${val.toLocaleString()}
                  </button>
                ))}
              </div>

              <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-200">
                Con <strong className="text-white">${bankroll.toLocaleString()}</strong> en plan{' '}
                <strong className="text-white">
                  {profile === 'conservative' ? 'Seguro' : profile === 'balanced' ? 'Equilibrado' : 'Arriesgado'}
                </strong>
                :<br />
                Apuesta{' '}
                <strong className="text-white font-mono">
                  ${(bankroll * (profile === 'conservative' ? 0.03 : profile === 'balanced' ? 0.05 : 0.1)).toFixed(2)}
                </strong>{' '}
                por pick · Retorno estimado{' '}
                <strong className="text-white font-mono">
                  ${(bankroll * (profile === 'conservative' ? 0.12 : profile === 'balanced' ? 0.2 : 0.3)).toFixed(0)} – $
                  {(bankroll * (profile === 'conservative' ? 0.18 : profile === 'balanced' ? 0.35 : 0.6)).toFixed(0)}
                </strong>
                /mes
              </div>
            </div>

            <div className="mt-8 flex justify-between">
              <button
                onClick={() => setStep(1)}
                className="px-6 py-2.5 text-zinc-400 hover:text-white font-semibold transition-colors"
              >
                Atrás
              </button>
              <button
                disabled={bankroll <= 0}
                onClick={() => setStep(3)}
                className="px-6 py-2.5 bg-white text-black font-semibold rounded-lg disabled:opacity-50 transition-opacity"
              >
                Continuar
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="animate-in fade-in slide-in-from-right-8">
            <h1 className="text-2xl font-bold font-sans tracking-tight mb-2">
              ¿Qué ligas te interesan?
            </h1>
            <p className="text-zinc-400 mb-8 text-sm">
              Selecciona al menos una liga para personalizar tu panel.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {LEAGUES.map((l) => {
                const active = favorites.includes(l.code);
                return (
                  <button
                    key={l.code}
                    onClick={() => toggleLeague(l.code)}
                    className={`p-4 rounded-xl border flex flex-col items-center justify-center gap-2 transition-all ${
                      active
                        ? 'border-amber-500 bg-amber-500/10 scale-[1.02]'
                        : 'border-white/10 hover:border-white/20 hover:bg-white/5'
                    }`}
                  >
                    <span className="text-2xl">{l.flag}</span>
                    <span className="text-sm font-semibold text-center">{l.name}</span>
                  </button>
                );
              })}
            </div>

            <div className="mt-12 flex justify-between">
              <button
                onClick={() => setStep(2)}
                className="px-6 py-2.5 text-zinc-400 hover:text-white font-semibold transition-colors"
              >
                Atrás
              </button>
              <button
                disabled={favorites.length === 0}
                onClick={() => setStep(4)}
                className="px-6 py-2.5 bg-white text-black font-semibold rounded-lg disabled:opacity-50 transition-opacity"
              >
                Continuar
              </button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="animate-in fade-in slide-in-from-right-8 text-center">
            <h1 className="text-3xl font-bold font-sans tracking-tight mb-8">
              Todo listo, {user.name}
            </h1>

            <div className="p-6 rounded-2xl bg-gradient-to-br from-amber-500/20 to-transparent border border-amber-500/30 text-left mb-8 max-w-md mx-auto">
              <div className="font-mono text-[10px] uppercase tracking-widest text-amber-500/80 mb-2">
                Tu Plan
              </div>
              <div className="text-lg font-bold mb-1">
                {profile === 'conservative' ? 'Seguro' : profile === 'balanced' ? 'Equilibrado' : 'Arriesgado'} · $
                {bankroll.toLocaleString()}
              </div>
              <div className="text-zinc-300 text-sm mb-4">
                {favorites.length} ligas seleccionadas
              </div>
              
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-amber-500/20">
                <div>
                  <div className="text-xs text-zinc-500 mb-1">Stake por pick</div>
                  <div className="font-mono text-white font-bold">
                    ${(bankroll * (profile === 'conservative' ? 0.03 : profile === 'balanced' ? 0.05 : 0.1)).toFixed(2)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500 mb-1">Retorno Est.</div>
                  <div className="font-mono text-emerald-400 font-bold">
                    ${(bankroll * (profile === 'conservative' ? 0.12 : profile === 'balanced' ? 0.2 : 0.3)).toFixed(0)}/mes
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-3 max-w-md mx-auto mb-10 text-left">
              <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10">
                <Shield className="w-5 h-5 text-emerald-400" />
                <span className="text-sm font-medium">Picks filtrados por ligas y perfil</span>
              </div>
              <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10">
                <Scale className="w-5 h-5 text-indigo-400" />
                <span className="text-sm font-medium">Bankroll tracker en tiempo real</span>
              </div>
              <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10">
                <Zap className="w-5 h-5 text-amber-400" />
                <span className="text-sm font-medium">Alertas inteligentes activadas</span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={handleFinish}
                disabled={loading}
                className="px-8 py-3 bg-white text-black font-bold rounded-xl hover:bg-zinc-200 transition-colors flex items-center justify-center min-w-[200px]"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Ir a mi dashboard'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
