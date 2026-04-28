'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, Check, Crown, Loader2, ShieldCheck, Sparkles, Star, TrendingUp } from 'lucide-react';

import Logo from '@/components/brand/Logo';
import { useAuth } from '@/contexts/AuthContext';

type Period = 'monthly' | 'yearly';
type TierId = 'free' | 'pro' | 'vip';

interface Tier {
  id: TierId;
  name: string;
  monthly: number;
  yearly: number;
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
    monthly: 0,
    yearly: 0,
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
    monthly: 19,
    yearly: 182,
    description: 'Para apostadores que toman esto en serio.',
    highlight: true,
    icon: <TrendingUp className="w-5 h-5" />,
    features: [
      'Todos los picks Free',
      'Picks Premium (edge 5-8%, EV 8-15%)',
      'Filtro por liga + alerta divergencia',
      'Stake sugerido (Kelly fraccional)',
      'Mercados de goles + córners',
      'Historial ilimitado + métricas ROI',
    ],
    cta: 'Suscribirme a Pro',
  },
  {
    id: 'vip',
    name: 'VIP',
    monthly: 79,
    yearly: 759,
    description: 'Máximo edge. Para bankrolls serios.',
    icon: <Crown className="w-5 h-5" />,
    features: [
      'Todos los picks Pro',
      'Picks VIP (edge ≥ 8%, EV ≥ 15%)',
      'Análisis Claude en lenguaje natural',
      'Alertas Telegram en tiempo real',
      'Bankroll tracker + backtesting',
      'Acceso anticipado a nuevas ligas',
      'Eventos exclusivos en México',
    ],
    cta: 'Suscribirme a VIP',
  },
];

const PENDING_KEY = 'edgebet.pricing.pending';

const TRUSTED_BY = ['Polymarket', 'Pinnacle', 'Football-Data', 'Stripe'];

const FAQ = [
  {
    q: '¿Cómo se calcula el edge de un pick?',
    a: 'Comparamos la probabilidad de nuestro modelo ML contra la implícita de la cuota bookie. Si el modelo asigna +5pp más, hay edge.',
  },
  {
    q: '¿Puedo cancelar cuando quiera?',
    a: 'Sí. Sin permanencia. Cancelas desde tu perfil y mantenés acceso hasta fin del periodo facturado.',
  },
  {
    q: '¿Qué incluye el plan VIP que no tiene Pro?',
    a: 'Picks con edge ≥ 8%, alertas Telegram instantáneas, análisis con Claude, backtesting y acceso anticipado a nuevas ligas.',
  },
  {
    q: '¿El plan anual tiene descuento?',
    a: 'Sí, 20% off comparado con mensual. Equivale a 2 meses gratis al año.',
  },
];

export default function PricingPage() {
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const [period, setPeriod] = useState<Period>('monthly');
  const [pendingTier, setPendingTier] = useState<TierId | null>(null);
  const [confirmation, setConfirmation] = useState<TierId | null>(null);

  const yearlySavingsPct = 20;

  const onSelect = (tier: Tier) => {
    if (tier.id === 'free') {
      if (!isAuthenticated) router.push('/register');
      else router.push('/dashboard');
      return;
    }

    setPendingTier(tier.id);
    if (!isAuthenticated) {
      window.localStorage.setItem(PENDING_KEY, JSON.stringify({ tier: tier.id, period }));
      router.push('/register?redirect=/pricing');
      return;
    }

    setTimeout(() => {
      window.localStorage.setItem(
        PENDING_KEY,
        JSON.stringify({ tier: tier.id, period, requestedAt: new Date().toISOString() }),
      );
      setPendingTier(null);
      setConfirmation(tier.id);
    }, 700);
  };

  useEffect(() => {
    if (!confirmation) return;
    const t = setTimeout(() => setConfirmation(null), 4500);
    return () => clearTimeout(t);
  }, [confirmation]);

  const currentTier: TierId | null = (user?.tier as TierId | undefined) ?? null;

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      <nav className="sticky top-0 z-40 bg-[#0a0a0c]/90 backdrop-blur-md border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 h-[68px] flex items-center justify-between">
          <Logo variant="horizontal" theme="dark" height={40} href="/" priority />
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="px-5 h-[40px] flex items-center bg-amber-400 text-[#0a0a0c] rounded-full text-[13px] font-sans font-bold hover:bg-amber-300 transition-colors"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden sm:block text-[13px] font-sans font-medium text-zinc-400 hover:text-white transition-colors"
                >
                  Iniciar sesión
                </Link>
                <Link
                  href="/register"
                  className="px-5 h-[40px] flex items-center bg-amber-400 text-[#0a0a0c] rounded-full text-[13px] font-sans font-bold hover:bg-amber-300 transition-colors"
                >
                  Crear cuenta
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <section className="relative max-w-7xl mx-auto px-6 lg:px-8 pt-20 md:pt-28 pb-16">
        <div
          className="absolute inset-x-0 top-0 h-[480px] -z-10 pointer-events-none opacity-60"
          style={{
            background:
              'radial-gradient(circle at 50% 0%, rgba(251,191,36,0.15) 0%, rgba(251,191,36,0) 55%)',
          }}
        />
        <div className="text-center mb-10 max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 font-mono text-[10px] uppercase tracking-widest font-bold mb-6">
            <Sparkles className="w-3 h-3" />
            Pricing
          </div>
          <h1 className="font-sans font-extrabold text-[36px] md:text-[52px] text-white tracking-tight leading-[1.05] mb-4">
            Elige tu nivel de <span className="text-amber-300">ventaja</span>
          </h1>
          <p className="font-sans text-[15px] md:text-[16px] text-zinc-400 max-w-xl mx-auto">
            Mismo modelo cuantitativo. Distintas profundidades de análisis. Cancelas cuando quieras.
          </p>
        </div>

        <PeriodSwitch period={period} onChange={setPeriod} savingsPct={yearlySavingsPct} />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-12">
          {TIERS.map((tier) => (
            <TierCard
              key={tier.id}
              tier={tier}
              period={period}
              currentTier={currentTier}
              pending={pendingTier === tier.id}
              onSelect={() => onSelect(tier)}
            />
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 mt-16 pt-8 border-t border-white/[0.06]">
          <div className="flex items-center gap-2 text-zinc-500 font-mono text-[10px] uppercase tracking-widest font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            Datos institucionales
          </div>
          {TRUSTED_BY.map((name) => (
            <span
              key={name}
              className="font-sans text-[12px] text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              {name}
            </span>
          ))}
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-6 lg:px-8 py-16 border-t border-white/[0.06]">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
          <div>
            <h2 className="font-sans font-bold text-[24px] md:text-[32px] text-white tracking-tight mb-3">
              Preguntas frecuentes
            </h2>
            <p className="font-sans text-[14px] text-zinc-400 max-w-md">
              Si no encuentras lo que buscas, escríbenos a{' '}
              <a href="mailto:hola@edgebet.app" className="text-amber-300 hover:underline">
                hola@edgebet.app
              </a>
              .
            </p>
          </div>
          <ul className="flex flex-col gap-3">
            {FAQ.map((item) => (
              <FaqItem key={item.q} q={item.q} a={item.a} />
            ))}
          </ul>
        </div>
      </section>

      <footer className="border-t border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 py-10 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo variant="horizontal" theme="dark" height={28} href="/" />
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
              Quantitative Architect
            </span>
          </div>
          <p className="font-sans text-[12px] text-zinc-500">
            Pagos procesados por Stripe. Cancelas cuando quieras desde tu perfil.
          </p>
        </div>
      </footer>

      {confirmation && (
        <ConfirmationToast tier={confirmation} period={period} onClose={() => setConfirmation(null)} />
      )}
    </div>
  );
}

function PeriodSwitch({
  period,
  onChange,
  savingsPct,
}: {
  period: Period;
  onChange: (p: Period) => void;
  savingsPct: number;
}) {
  return (
    <div className="flex justify-center">
      <div className="inline-flex items-center bg-white/[0.03] rounded-full p-1 border border-white/[0.08]">
        <button
          type="button"
          onClick={() => onChange('monthly')}
          className={`h-[36px] px-5 rounded-full font-sans text-[13px] font-semibold transition-colors ${
            period === 'monthly'
              ? 'bg-white text-[#0a0a0c] shadow-sm'
              : 'text-zinc-400 hover:text-white'
          }`}
        >
          Mensual
        </button>
        <button
          type="button"
          onClick={() => onChange('yearly')}
          className={`h-[36px] px-5 rounded-full font-sans text-[13px] font-semibold transition-colors flex items-center gap-2 ${
            period === 'yearly'
              ? 'bg-white text-[#0a0a0c] shadow-sm'
              : 'text-zinc-400 hover:text-white'
          }`}
        >
          Anual
          <span
            className={`font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full ${
              period === 'yearly'
                ? 'bg-emerald-500/15 text-emerald-600'
                : 'bg-emerald-500/15 text-emerald-300'
            }`}
          >
            -{savingsPct}%
          </span>
        </button>
      </div>
    </div>
  );
}

function TierCard({
  tier,
  period,
  currentTier,
  pending,
  onSelect,
}: {
  tier: Tier;
  period: Period;
  currentTier: TierId | null;
  pending: boolean;
  onSelect: () => void;
}) {
  const isCurrent = currentTier === tier.id;
  const price = period === 'monthly' ? tier.monthly : tier.yearly;
  const periodLabel =
    tier.id === 'free' ? 'siempre' : period === 'monthly' ? '/ mes' : '/ año';

  const monthlyEquivalent = useMemo(() => {
    if (period !== 'yearly' || tier.yearly === 0) return null;
    return (tier.yearly / 12).toFixed(2);
  }, [period, tier.yearly]);

  const cardClass = tier.highlight
    ? 'bg-gradient-to-b from-amber-500/[0.08] to-[#111114] border-amber-500/30 md:scale-[1.03] shadow-[0_0_60px_rgba(251,191,36,0.08)]'
    : 'bg-[#111114] border-white/[0.08]';

  const accentClass = tier.id === 'vip' ? 'text-amber-300' : tier.highlight ? 'text-amber-300' : 'text-zinc-300';

  const buttonClass = tier.highlight
    ? 'bg-amber-400 text-[#0a0a0c] hover:bg-amber-300'
    : tier.id === 'vip'
      ? 'bg-white text-[#0a0a0c] hover:bg-zinc-200'
      : 'bg-white/[0.06] text-white border border-white/[0.08] hover:bg-white/[0.1]';

  return (
    <div
      className={`relative rounded-3xl border p-7 md:p-8 flex flex-col ${cardClass}`}
    >
      {tier.highlight && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-amber-400 text-[#0a0a0c] font-mono text-[10px] font-extrabold uppercase tracking-widest">
          Más popular
        </div>
      )}

      <div className={`flex items-center gap-2 mb-3 ${accentClass}`}>
        {tier.icon}
        <span className="font-sans font-bold text-[16px] text-white">{tier.name}</span>
      </div>

      <div className="mb-1 flex items-baseline gap-2">
        <span className="font-mono font-extrabold text-[44px] text-white tracking-tight">
          €{price}
        </span>
        <span className="font-sans text-[13px] text-zinc-500">{periodLabel}</span>
      </div>
      {monthlyEquivalent && (
        <p className="font-sans text-[12px] text-zinc-500 mb-1">
          Equivale a €{monthlyEquivalent} / mes
        </p>
      )}
      <p className="font-sans text-[13px] text-zinc-400 mb-6">{tier.description}</p>

      <ul className="flex flex-col gap-2.5 mb-7">
        {tier.features.map((f) => (
          <li key={f} className="flex items-start gap-2 font-sans text-[13px] text-zinc-200">
            <Check className={`w-4 h-4 mt-0.5 shrink-0 ${tier.highlight ? 'text-amber-300' : 'text-emerald-400'}`} />
            <span>{f}</span>
          </li>
        ))}
      </ul>

      {isCurrent ? (
        <div className="mt-auto w-full h-[48px] rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center font-sans font-semibold text-[13px] text-zinc-400">
          Tu plan actual
        </div>
      ) : (
        <button
          type="button"
          onClick={onSelect}
          disabled={pending}
          className={`mt-auto w-full h-[48px] rounded-full flex items-center justify-center gap-2 font-sans font-bold text-[14px] transition-colors disabled:opacity-70 disabled:cursor-not-allowed ${buttonClass}`}
        >
          {pending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Procesando…
            </>
          ) : (
            <>
              {tier.cta}
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      )}
    </div>
  );
}

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="rounded-xl border border-white/[0.06] bg-[#111114] overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full px-5 py-4 flex items-center justify-between gap-4 text-left hover:bg-white/[0.02] transition-colors"
      >
        <span className="font-sans font-semibold text-[14px] text-white">{q}</span>
        <span
          className={`font-mono text-[20px] text-zinc-500 transition-transform ${open ? 'rotate-45' : ''}`}
        >
          +
        </span>
      </button>
      {open && (
        <div className="px-5 pb-5 pt-0 font-sans text-[13px] text-zinc-400 leading-relaxed">
          {a}
        </div>
      )}
    </li>
  );
}

function ConfirmationToast({
  tier,
  period,
  onClose,
}: {
  tier: TierId;
  period: Period;
  onClose: () => void;
}) {
  const tierName = TIERS.find((t) => t.id === tier)?.name ?? tier;
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-4 rounded-2xl bg-[#16161a] text-white shadow-2xl shadow-black/40 border border-white/[0.08] flex items-center gap-4 max-w-md">
      <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-300 flex items-center justify-center">
        <Check className="w-5 h-5" />
      </div>
      <div className="flex-1">
        <div className="font-sans font-bold text-[14px]">Plan {tierName} reservado</div>
        <p className="font-sans text-[12px] text-zinc-400 mt-0.5">
          Pago {period === 'monthly' ? 'mensual' : 'anual'} pendiente. Te avisaremos cuando Stripe esté listo
          para confirmar.
        </p>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="font-sans text-[12px] text-zinc-500 hover:text-white"
      >
        Cerrar
      </button>
    </div>
  );
}
