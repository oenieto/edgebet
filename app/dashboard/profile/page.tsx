'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Crown, Mail, Shield, Wallet, Scale, Zap, Minus, Plus, Loader2, Edit2, TrendingUp, Save } from 'lucide-react';
import Link from 'next/link';

import { useAuth } from '@/contexts/AuthContext';
import { useUserStore } from '@/lib/store/userStore';
import { apiFetch } from '@/lib/api/client';

export default function ProfilePage() {
  const { user, token } = useAuth();
  const { profile: storeProfile, setProfile: setStoreProfile, bankroll: storeBankroll } = useUserStore();

  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  
  // Local state for editing
  const [bankroll, setBankroll] = useState(storeProfile?.bankroll ?? 1000);
  const [risk, setRisk] = useState<'conservative' | 'balanced' | 'aggressive'>(storeProfile?.risk_profile ?? 'balanced');
  const [isEditingBankroll, setIsEditingBankroll] = useState(false);

  useEffect(() => {
    if (storeProfile) {
      setBankroll(storeProfile.bankroll);
      setRisk(storeProfile.risk_profile);
    }
  }, [storeProfile]);

  if (!user) return null;

  const handleSave = async () => {
    const currentToken = token || window.localStorage.getItem('edgebet.auth.token');
    if (!user || !currentToken) return;
    setLoading(true);
    setSuccessMsg('');
    try {
      await apiFetch(`/user/${user.id}/profile`, {
        method: 'POST',
        token: currentToken,
        body: {
          risk_profile: risk,
          bankroll,
          horizon: storeProfile?.horizon || '1mes',
          favorite_leagues: storeProfile?.favorite_leagues || [],
        },
      });
      
      // Update local store
      if (storeProfile) {
        setStoreProfile({ ...storeProfile, bankroll, risk_profile: risk });
      } else {
        setStoreProfile({
          risk_profile: risk,
          bankroll,
          horizon: '1mes',
          stake_pct: risk === 'conservative' ? 3 : risk === 'balanced' ? 5 : 10,
          weekly_limit: bankroll * 0.20,
          daily_limit: bankroll * 0.10,
          favorite_leagues: []
        });
      }
      setIsEditingBankroll(false);
      setSuccessMsg('Perfil actualizado correctamente');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (e) {
      console.error(e);
      alert('Error guardando perfil. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const tierClass =
    user.tier === 'vip'
      ? 'bg-gradient-to-r from-amber-500/20 to-amber-600/20 text-amber-300 border border-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.15)]'
      : user.tier === 'pro'
        ? 'bg-gradient-to-r from-white/10 to-white/5 text-white border border-white/20 shadow-[0_0_15px_rgba(255,255,255,0.05)]'
        : 'bg-white/5 text-zinc-400 border border-white/[0.06]';

  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 lg:px-8 py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
        <h1 className="font-sans font-extrabold text-[32px] md:text-[40px] text-white tracking-tight leading-tight">
          Mi <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-zinc-500">Cuenta</span>
        </h1>
        <p className="font-sans text-[15px] text-zinc-400 mt-2">
          Gestiona tus datos personales, preferencias de riesgo y plan de suscripción.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: IDENTITY & PLAN */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="lg:col-span-1 flex flex-col gap-6">
          
          <div className="relative bg-[#111114] border border-white/[0.06] rounded-3xl p-8 overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="flex flex-col items-center text-center relative z-10">
              <div className="relative mb-6">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-zinc-800 to-zinc-900 border border-white/10 text-white flex items-center justify-center font-mono text-[40px] font-bold shadow-2xl">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                {user.tier === 'vip' && (
                  <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-amber-500 rounded-full flex items-center justify-center text-black border-4 border-[#111114] shadow-[0_0_10px_rgba(245,158,11,0.5)]">
                    <Crown className="w-4 h-4" strokeWidth={3} />
                  </div>
                )}
              </div>
              <h2 className="font-sans font-bold text-[22px] text-white mb-1">{user.name}</h2>
              <p className="font-sans text-[14px] text-zinc-400 mb-6">{user.email}</p>
              
              <span className={`inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-widest px-4 py-1.5 rounded-full font-bold ${tierClass}`}>
                {user.tier === 'vip' ? <Crown className="w-3.5 h-3.5" /> : null}
                {user.tier} Plan
              </span>
            </div>
            
            <div className="mt-8 pt-6 border-t border-white/[0.06] flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-zinc-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span className="font-sans text-[13px]">Miembro desde</span>
                </div>
                <span className="font-mono text-[13px] text-white font-medium">{user.created_at.slice(0, 10)}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-zinc-400">
                  <Shield className="w-4 h-4" />
                  <span className="font-sans text-[13px]">Seguridad</span>
                </div>
                <span className="font-sans text-[13px] text-emerald-400 font-medium bg-emerald-400/10 px-2 py-0.5 rounded-full">Protegida</span>
              </div>
            </div>
          </div>

          {user.tier !== 'vip' && (
            <div className="bg-gradient-to-br from-amber-500/20 to-transparent border border-amber-500/30 rounded-3xl p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 blur-3xl rounded-full" />
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-3">
                  <Crown className="w-5 h-5 text-amber-400" />
                  <h3 className="font-sans font-bold text-[18px] text-amber-400">Pásate a VIP</h3>
                </div>
                <p className="font-sans text-[13px] text-zinc-300 mb-5 leading-relaxed">
                  Desbloquea el Pick del Día exclusivo, alertas por Telegram y picks con edge &gt;= 8%.
                </p>
                <Link
                  href="/pricing"
                  className="w-full h-[40px] flex items-center justify-center bg-amber-500 text-black rounded-xl font-sans font-bold text-[13px] hover:bg-amber-400 transition-colors shadow-[0_0_15px_rgba(245,158,11,0.2)]"
                >
                  Ver beneficios VIP
                </Link>
              </div>
            </div>
          )}

        </motion.div>

        {/* RIGHT COLUMN: PREFERENCES */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          
          <AnimatePresence>
            {successMsg && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-2xl p-4 flex items-center gap-3 text-emerald-400 mb-2">
                  <CheckCircle2 className="w-5 h-5 shrink-0" />
                  <span className="font-sans font-medium text-[14px]">{successMsg}</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* BANKROLL SECTION */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-[#111114] border border-white/[0.06] rounded-3xl p-6 md:p-8">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="font-sans font-bold text-[20px] text-white flex items-center gap-2">
                  <Wallet className="w-5 h-5 text-emerald-400" />
                  Capital de Inversión (Bankroll)
                </h2>
                <p className="font-sans text-[13px] text-zinc-400 mt-1">
                  Tu saldo total dedicado a apuestas. Usado para calcular el stake sugerido.
                </p>
              </div>
              {!isEditingBankroll && (
                <button 
                  onClick={() => setIsEditingBankroll(true)}
                  className="w-9 h-9 flex items-center justify-center rounded-full bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              )}
            </div>

            {isEditingBankroll ? (
              <div className="bg-white/[0.02] border border-white/[0.08] rounded-2xl p-6">
                <div className="flex items-center justify-center gap-4 mb-6">
                  <button
                    onClick={() => setBankroll((prev) => Math.max(50, prev - 100))}
                    className="w-12 h-12 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors border border-white/5 text-zinc-300 hover:text-white"
                  >
                    <Minus className="w-5 h-5" />
                  </button>
                  <div className="flex items-center justify-center font-mono font-bold text-white min-w-[160px]">
                    <span className="text-emerald-400 mr-2 text-4xl">$</span>
                    <input
                      type="number"
                      value={bankroll}
                      onChange={(e) => setBankroll(Number(e.target.value))}
                      className="bg-transparent outline-none w-full text-center text-5xl [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none focus:ring-0"
                    />
                  </div>
                  <button
                    onClick={() => setBankroll((prev) => Math.min(50000, prev + 100))}
                    className="w-12 h-12 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors border border-white/5 text-zinc-300 hover:text-white"
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                </div>
                
                <input
                  type="range"
                  min="50"
                  max="20000"
                  step="50"
                  value={bankroll}
                  onChange={(e) => setBankroll(Number(e.target.value))}
                  className="w-full accent-emerald-500 mb-8"
                />

                <div className="flex justify-end gap-3">
                  <button 
                    onClick={() => { setIsEditingBankroll(false); setBankroll(storeProfile?.bankroll ?? 1000); }}
                    className="px-5 py-2 rounded-xl font-sans text-[13px] font-semibold text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
                  >
                    Cancelar
                  </button>
                  <button 
                    onClick={handleSave}
                    disabled={loading}
                    className="px-5 py-2 rounded-xl font-sans text-[13px] font-bold bg-white text-black hover:bg-zinc-200 transition-colors flex items-center gap-2"
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Save className="w-4 h-4" /> Guardar Bankroll</>}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-end gap-4">
                <div className="font-mono font-bold text-[48px] text-white leading-none tracking-tight">
                  <span className="text-emerald-400 mr-1">$</span>
                  {bankroll.toLocaleString()}
                </div>
                {storeBankroll?.pnl_pct !== undefined && storeBankroll.pnl_pct !== 0 && (
                  <div className={`mb-2 flex items-center gap-1 font-mono text-[14px] font-bold px-3 py-1 rounded-full ${storeBankroll.pnl_pct > 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                    <TrendingUp className="w-4 h-4" />
                    {storeBankroll.pnl_pct > 0 ? '+' : ''}{storeBankroll.pnl_pct.toFixed(1)}% vs inicio
                  </div>
                )}
              </div>
            )}
          </motion.div>

          {/* RISK PROFILE SECTION */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="bg-[#111114] border border-white/[0.06] rounded-3xl p-6 md:p-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="font-sans font-bold text-[20px] text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-indigo-400" />
                  Perfil de Riesgo
                </h2>
                <p className="font-sans text-[13px] text-zinc-400 mt-1">
                  Determina cómo filtramos tus picks y el % de stake máximo recomendado.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <RiskCard 
                type="conservative"
                selected={risk === 'conservative'}
                onClick={() => setRisk('conservative')}
                icon={<Shield className="w-5 h-5 text-emerald-400" />}
                title="Seguro"
                desc="Stake 3%. Picks de alta confianza (>68%). Crecimiento estable."
                color="emerald"
              />
              <RiskCard 
                type="balanced"
                selected={risk === 'balanced'}
                onClick={() => setRisk('balanced')}
                icon={<Scale className="w-5 h-5 text-indigo-400" />}
                title="Equilibrado"
                desc="Stake 5%. El mejor balance entre riesgo y beneficio (>60%)."
                color="indigo"
                recommended
              />
              <RiskCard 
                type="aggressive"
                selected={risk === 'aggressive'}
                onClick={() => setRisk('aggressive')}
                icon={<Zap className="w-5 h-5 text-red-400" />}
                title="Arriesgado"
                desc="Stake 10%. Mayor volatilidad, retorno alto potencial."
                color="red"
              />
            </div>

            {storeProfile?.risk_profile !== risk && (
              <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
                <button 
                  onClick={handleSave}
                  disabled={loading}
                  className="px-6 py-2.5 rounded-xl font-sans text-[14px] font-bold bg-indigo-500 text-white hover:bg-indigo-400 transition-colors shadow-[0_0_15px_rgba(99,102,241,0.3)] flex items-center gap-2"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Actualizar Perfil'}
                </button>
              </motion.div>
            )}

          </motion.div>

        </div>
      </div>
    </div>
  );
}

function RiskCard({
  type,
  selected,
  onClick,
  icon,
  title,
  desc,
  color,
  recommended
}: {
  type: string;
  selected: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  desc: string;
  color: 'emerald' | 'indigo' | 'red';
  recommended?: boolean;
}) {
  
  const colorMap = {
    emerald: 'border-emerald-500/50 bg-emerald-500/10 shadow-[0_0_15px_rgba(16,185,129,0.1)]',
    indigo: 'border-indigo-500/50 bg-indigo-500/10 shadow-[0_0_15px_rgba(99,102,241,0.15)]',
    red: 'border-red-500/50 bg-red-500/10 shadow-[0_0_15px_rgba(239,68,68,0.1)]'
  };

  const activeClass = selected ? colorMap[color] : 'border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/20';

  return (
    <div 
      onClick={onClick}
      className={`relative p-5 rounded-2xl border transition-all duration-300 cursor-pointer overflow-hidden ${activeClass}`}
    >
      {recommended && (
        <div className="absolute top-0 right-0 bg-indigo-500 text-white text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded-bl-lg z-10">
          Recomendado
        </div>
      )}
      
      {selected && (
        <div className={`absolute -right-4 -top-4 w-16 h-16 blur-2xl rounded-full opacity-50 bg-${color}-500 pointer-events-none`} />
      )}

      <div className={`w-10 h-10 rounded-xl mb-4 flex items-center justify-center ${selected ? 'bg-white/10' : 'bg-[#16161a] border border-white/[0.05]'}`}>
        {icon}
      </div>
      <h3 className="font-sans font-bold text-[16px] text-white mb-1">{title}</h3>
      <p className="font-sans text-[12px] text-zinc-400 leading-relaxed">{desc}</p>
    </div>
  );
}
