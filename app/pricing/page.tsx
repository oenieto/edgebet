'use client';

import Link from 'next/link';
import { Check, Crown, Star, TrendingUp, CreditCard } from 'lucide-react';

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
    <div className="min-h-screen bg-background text-on-surface">
      <nav className="bg-surface/90 backdrop-blur sticky top-0 z-40 border-b border-surface-container-high">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 h-[60px] flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-primary" />
            <span className="font-sans font-bold text-[20px] tracking-tight text-on-surface">
              Edge<span className="font-normal text-tertiary">bet</span>
            </span>
          </Link>
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="px-5 h-[36px] flex items-center bg-primary text-white rounded-full text-[13px] font-sans font-semibold hover:opacity-90 transition-opacity"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-[14px] font-sans font-medium text-on-surface-variant hover:text-primary transition-colors"
                >
                  Iniciar sesión
                </Link>
                <Link
                  href="/register"
                  className="px-5 h-[36px] flex items-center bg-primary text-white rounded-full text-[13px] font-sans font-semibold hover:opacity-90 transition-opacity"
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
          <p className="font-sans text-[16px] text-tertiary">
            Todos los picks se calculan con el mismo modelo. La diferencia está en cuántos
            puedes ver y qué profundidad de análisis recibes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {TIERS.map((tier) => (
            <TierCard key={tier.id} tier={tier} currentTier={user?.tier ?? null} />
          ))}
        </div>

        <div className="mt-12 max-w-xl mx-auto bg-surface-container-lowest border border-surface-container-high rounded-xl p-4 flex items-center gap-3 shadow-sm">
          <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center flex-shrink-0">
            <CreditCard className="w-5 h-5 text-primary" />
          </div>
          <p className="text-left text-on-surface-variant font-sans text-[13px] leading-relaxed">
            <strong className="text-on-surface block mb-0.5">Integración Stripe Ready</strong>
            El sistema de procesamiento de pagos está preparado para conectarse con Stripe Checkout. Los botones de suscripción redirigirán al flujo de pago seguro.
          </p>
        </div>
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
  
  // Dashboard Design System applied to pricing cards
  const cardClass = tier.highlight
    ? 'bg-secondary/5 border-secondary md:scale-[1.02] shadow-xl shadow-secondary/5'
    : tier.id === 'vip' 
      ? 'bg-warning/5 border-warning/50'
      : 'bg-surface-container-lowest border-surface-container-low';
      
  const iconClass = tier.highlight 
    ? 'text-secondary' 
    : tier.id === 'vip' 
      ? 'text-warning' 
      : 'text-primary';
      
  const priceClass = tier.highlight 
    ? 'text-on-surface' 
    : tier.id === 'vip' 
      ? 'text-on-surface' 
      : 'text-on-surface';
      
  const descClass = 'text-tertiary';
  
  const checkClass = tier.highlight 
    ? 'text-secondary' 
    : tier.id === 'vip' 
      ? 'text-warning' 
      : 'text-primary';
      
  const featureClass = 'text-on-surface-variant';

  const buttonClass = tier.highlight
    ? 'bg-secondary text-white hover:opacity-90'
    : tier.id === 'vip'
      ? 'bg-warning text-white hover:opacity-90'
      : 'bg-primary text-white hover:opacity-90';

  return (
    <div
      className={`rounded-3xl border p-7 md:p-8 flex flex-col transition-all ${cardClass}`}
    >
      {tier.highlight && (
        <div className="self-start mb-4 px-2.5 py-0.5 rounded-md bg-secondary-container text-on-secondary-container font-mono text-[11px] font-bold uppercase tracking-widest border border-secondary/20">
          Más popular
        </div>
      )}

      <div className="flex items-center gap-2 mb-2">
        <span className={iconClass}>{tier.icon}</span>
        <span className="font-sans font-bold text-[18px] text-on-surface">{tier.name}</span>
      </div>

      <div className="mb-2 flex items-baseline gap-2">
        <span className={`font-mono font-bold text-[36px] ${priceClass}`}>{tier.price}</span>
        <span className={`font-sans text-[14px] ${descClass}`}>/ {tier.period}</span>
      </div>
      <p className={`font-sans text-[14px] mb-6 ${descClass}`}>{tier.description}</p>

      <ul className="flex flex-col gap-3 mb-8">
        {tier.features.map((f) => (
          <li key={f} className="flex items-start gap-2.5 font-sans text-[14px]">
            <Check className={`w-4 h-4 mt-0.5 shrink-0 ${checkClass}`} />
            <span className={featureClass}>{f}</span>
          </li>
        ))}
      </ul>

      {isCurrent ? (
        <div className="mt-auto w-full h-[48px] rounded-full bg-surface-container-high border border-surface-container-highest flex items-center justify-center font-sans font-semibold text-[14px] text-tertiary">
          Tu plan actual
        </div>
      ) : (
        <Link
          href={currentTier ? '/dashboard' : '/api/checkout/session'}
          className={`mt-auto w-full h-[48px] rounded-full flex items-center justify-center font-sans font-semibold text-[14px] transition-opacity ${buttonClass}`}
        >
          {tier.cta}
        </Link>
      )}
    </div>
  );
}
