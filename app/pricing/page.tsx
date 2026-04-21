'use client';

import Link from 'next/link';
import { Check, Crown, Star, TrendingUp } from 'lucide-react';

import { useAuth } from '@/contexts/AuthContext';

interface Tier {
  id: 'free' | 'pro' | 'vip';
  name: string;
  price: string;
  period: string;
  description: string;
  highlight?: boolean;
  icon: React.ReactNode;
  features: string[];
  cta: string;
}

const TIERS: Tier[] = [
  {
    id: 'free',
    name: 'Free',
    price: '€0',
    period: 'siempre',
    description: 'Para empezar a probar nuestro sistema.',
    icon: <Star className="w-5 h-5" />,
    features: [
      '1 pick diario con edge ≥ 3%',
      'Probabilidades ML + cuotas bookie',
      'Accuracy tracking público',
      'Historial 30 días',
    ],
    cta: 'Empezar gratis',
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '€19',
    period: 'por mes',
    description: 'Para apostadores que toman esto en serio.',
    highlight: true,
    icon: <TrendingUp className="w-5 h-5" />,
    features: [
      'Todos los picks Free',
      'Picks Premium (edge 5-8%, EV 8-15%)',
      'Filtro por liga + alerta divergencia',
      'Stake sugerido (Kelly fraccional)',
      'Historial ilimitado + métricas ROI',
    ],
    cta: 'Suscribirme a Pro',
  },
  {
    id: 'vip',
    name: 'VIP',
    price: '€79',
    period: 'por mes',
    description: 'Máximo edge. Para bankrolls serios.',
    icon: <Crown className="w-5 h-5" />,
    features: [
      'Todos los picks Pro',
      'Picks VIP (edge ≥ 8%, EV ≥ 15%)',
      'Análisis Claude en lenguaje natural',
      'Alertas Telegram en tiempo real',
      'Bankroll tracker + backtesting',
      'Acceso anticipado a nuevas ligas',
    ],
    cta: 'Suscribirme a VIP',
  },
];

export default function PricingPage() {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <nav className="bg-white/90 backdrop-blur sticky top-0 z-40 border-b border-surface-container-high">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 h-[60px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            <span className="font-sans text-[17px] tracking-tight">
              <span className="font-bold text-slate-900">Edge</span>
              <span className="font-normal text-slate-500">bet</span>
            </span>
          </Link>
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="px-4 h-[36px] flex items-center bg-primary text-white rounded-full text-[13px] font-sans font-semibold hover:opacity-90"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-[13px] font-sans font-medium text-slate-600 hover:text-slate-900"
                >
                  Iniciar sesión
                </Link>
                <Link
                  href="/register"
                  className="px-4 h-[36px] flex items-center bg-primary text-white rounded-full text-[13px] font-sans font-semibold hover:opacity-90"
                >
                  Crear cuenta
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <section className="max-w-7xl mx-auto px-6 lg:px-8 py-16 md:py-24">
        <div className="text-center mb-12 max-w-2xl mx-auto">
          <h1 className="font-sans font-bold text-[32px] md:text-[44px] text-on-surface tracking-tight mb-3">
            Elige tu nivel de ventaja
          </h1>
          <p className="font-sans text-[15px] text-tertiary">
            Todos los picks se calculan con el mismo modelo. La diferencia está en cuántos
            puedes ver y qué profundidad de análisis recibes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {TIERS.map((tier) => (
            <TierCard key={tier.id} tier={tier} currentTier={user?.tier ?? null} />
          ))}
        </div>

        <p className="text-center text-tertiary font-sans text-[12px] mt-10 max-w-xl mx-auto">
          El pago aún no está conectado. Esta página existe como referencia del modelo de
          pricing — se integrará con Stripe en la próxima fase.
        </p>
      </section>
    </div>
  );
}

function TierCard({
  tier,
  currentTier,
}: {
  tier: Tier;
  currentTier: 'free' | 'pro' | 'vip' | null;
}) {
  const isCurrent = currentTier === tier.id;
  const cardClass = tier.highlight
    ? 'bg-slate-900 text-white border-slate-900 md:scale-[1.02]'
    : 'bg-surface-container-lowest text-on-surface border-surface-container-low';
  const priceClass = tier.highlight ? 'text-white' : 'text-on-surface';
  const descClass = tier.highlight ? 'text-slate-300' : 'text-tertiary';
  const checkClass = tier.highlight ? 'text-emerald-400' : 'text-primary';
  const featureClass = tier.highlight ? 'text-slate-200' : 'text-on-surface-variant';

  const buttonClass = tier.highlight
    ? 'bg-white text-slate-900 hover:bg-slate-100'
    : tier.id === 'vip'
      ? 'bg-amber-500 text-white hover:bg-amber-600'
      : 'bg-primary text-white hover:opacity-90';

  return (
    <div
      className={`rounded-3xl border p-7 md:p-8 flex flex-col ${cardClass} ${
        tier.highlight ? 'shadow-xl shadow-slate-900/20' : ''
      }`}
    >
      {tier.highlight && (
        <div className="self-start mb-4 px-2.5 py-0.5 rounded-full bg-amber-400/20 text-amber-300 font-mono text-[10px] font-bold uppercase tracking-widest">
          Más popular
        </div>
      )}

      <div className="flex items-center gap-2 mb-2">
        <span className={tier.highlight ? 'text-amber-400' : 'text-primary'}>{tier.icon}</span>
        <span className="font-sans font-bold text-[16px]">{tier.name}</span>
      </div>

      <div className="mb-2 flex items-baseline gap-2">
        <span className={`font-mono font-bold text-[36px] ${priceClass}`}>{tier.price}</span>
        <span className={`font-sans text-[13px] ${descClass}`}>/ {tier.period}</span>
      </div>
      <p className={`font-sans text-[13px] mb-6 ${descClass}`}>{tier.description}</p>

      <ul className="flex flex-col gap-2.5 mb-7">
        {tier.features.map((f) => (
          <li key={f} className="flex items-start gap-2 font-sans text-[13px]">
            <Check className={`w-4 h-4 mt-0.5 shrink-0 ${checkClass}`} />
            <span className={featureClass}>{f}</span>
          </li>
        ))}
      </ul>

      {isCurrent ? (
        <div className="mt-auto w-full h-[48px] rounded-full bg-white/10 border border-current/20 flex items-center justify-center font-sans font-semibold text-[14px] opacity-80">
          Tu plan actual
        </div>
      ) : (
        <Link
          href={currentTier ? '/dashboard' : '/register'}
          className={`mt-auto w-full h-[48px] rounded-full flex items-center justify-center font-sans font-semibold text-[14px] transition-colors ${buttonClass}`}
        >
          {tier.cta}
        </Link>
      )}
    </div>
  );
}
