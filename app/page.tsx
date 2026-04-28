'use client';

import Link from 'next/link';
import { Activity, ArrowRight, Brain, CheckCircle2, LineChart, Lock, LogOut, ShieldCheck, Target, Zap } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import Logo from '@/components/brand/Logo';

export default function HomePage() {
  const { user, isAuthenticated, isHydrated, logout } = useAuth();
  const primaryCtaHref = isAuthenticated ? '/dashboard' : '/register';
  const primaryCtaLabel = isAuthenticated ? 'Ir al dashboard' : 'Empezar gratis';

  return (
    <div className="min-h-screen bg-background text-on-surface selection:bg-amber-500/30 selection:text-amber-900">
      {/* Section 1: Premium Navbar */}
      <nav className="sticky top-0 z-50 bg-[#0a0a0c]/85 backdrop-blur-xl border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 h-[68px] flex items-center justify-between gap-6">
          <div className="flex items-center gap-10">
            <Logo variant="horizontal" theme="dark" height={36} href="/" priority />
            <div className="hidden md:flex items-center gap-1">
              <NavLink href="#como-funciona" label="Cómo funciona" />
              <NavLink href="#picks-dia" label="Picks del día" active />
              <NavLink
                href={isAuthenticated ? '/dashboard/history' : '/login'}
                label="Historial"
              />
              <NavLink href="/pricing" label="Precios" />
              <NavLink href="#comunidad" label="Comunidad" />
            </div>
          </div>

          <div className="flex items-center gap-3">
            {isHydrated && isAuthenticated && user ? (
              <>
                <Link
                  href="/dashboard/profile"
                  className="hidden md:inline-flex items-center gap-2 h-[36px] px-3 rounded-full bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.08] transition-colors"
                >
                  <span className="w-6 h-6 rounded-full bg-amber-400/15 text-amber-300 flex items-center justify-center font-mono text-[11px] font-bold">
                    {user.name.charAt(0).toUpperCase()}
                  </span>
                  <span className="font-sans text-[13px] font-medium text-zinc-200 max-w-[120px] truncate">
                    {user.name}
                  </span>
                </Link>
                <Link
                  href="/dashboard"
                  className="h-[40px] px-5 inline-flex items-center bg-amber-400 text-[#0a0a0c] rounded-full font-sans font-bold text-[13px] hover:bg-amber-300 transition-colors"
                >
                  Dashboard
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  aria-label="Cerrar sesión"
                  className="text-zinc-500 hover:text-white transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden sm:block font-sans text-[13px] font-medium text-zinc-400 hover:text-white transition-colors"
                >
                  Iniciar sesión
                </Link>
                <Link
                  href={primaryCtaHref}
                  className="h-[40px] px-5 inline-flex items-center gap-1.5 bg-amber-400 text-[#0a0a0c] rounded-full font-sans font-bold text-[13px] hover:bg-amber-300 transition-colors shadow-[0_0_30px_rgba(251,191,36,0.18)]"
                >
                  {primaryCtaLabel}
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Section 2: Hero */}
      <section className="bg-[#0a0a0c] text-white pt-24 pb-32 px-8 overflow-hidden relative">
        <div className="absolute inset-0 z-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 70% 30%, #fcd34d 0%, transparent 50%)' }}></div>
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 relative z-10 items-center">
          <div className="space-y-8">
            <div className="inline-flex items-center px-3 py-1 rounded-full border border-amber-500/20 bg-amber-500/10 text-amber-300 text-sm font-medium font-mono mb-4">
              <span className="w-2 h-2 rounded-full bg-amber-400 mr-2 animate-pulse"></span>
              IA · Polymarket · Pinnacle API
            </div>
            <h1 className="text-5xl lg:text-7xl font-extrabold leading-tight tracking-tight text-white">
              El <span className="text-amber-300">edge</span> que los tipsters no tienen.
            </h1>
            <p className="text-xl text-zinc-400 max-w-lg leading-relaxed">
              Arquitectura cuantitativa para el mercado de fútbol. Detectamos divergencias de probabilidad en tiempo real cruzando datos de exchanges predictivos y casas de apuestas institucionales.
            </p>
            <div className="flex items-center space-x-4 pt-4">
              <Link href={primaryCtaHref} className="bg-amber-400 text-black rounded-full px-8 py-4 font-bold text-lg hover:bg-amber-500 transition-all flex items-center shadow-[0_0_30px_rgba(251,191,36,0.2)]">
                {isAuthenticated ? 'Ir al dashboard' : 'Ver picks abiertos'}
                <ArrowRight className="ml-2 w-5 h-5" />
              </Link>
            </div>
            <div className="flex items-center space-x-8 pt-8 border-t border-white/[0.06] mt-8">
              <div>
                <div className="font-mono text-2xl font-bold text-amber-300">61.4%</div>
                <div className="text-sm text-zinc-500 mt-1 uppercase tracking-widest text-[10px]">Accuracy (L30)</div>
              </div>
              <div className="w-px h-10 bg-white/[0.06]"></div>
              <div>
                <div className="font-mono text-2xl font-bold text-white">15+</div>
                <div className="text-sm text-zinc-500 mt-1 uppercase tracking-widest text-[10px]">Ligas Modeladas</div>
              </div>
              <div className="w-px h-10 bg-white/[0.06]"></div>
              <div>
                <div className="font-mono text-2xl font-bold text-white">100%</div>
                <div className="text-sm text-zinc-500 mt-1 uppercase tracking-widest text-[10px]">Historial Auditado</div>
              </div>
            </div>
          </div>

          <div className="relative lg:ml-auto w-full max-w-md">
            <div className="absolute -inset-4 bg-gradient-to-r from-amber-400 to-amber-600 opacity-10 blur-2xl rounded-[3rem]"></div>
            <div className="bg-[#0a0a0c] border border-white/[0.06] rounded-2xl p-6 shadow-2xl relative z-10 backdrop-blur-xl">
              <div className="flex justify-between items-center mb-6">
                <span className="text-xs font-bold text-zinc-400 tracking-wider uppercase">Pick Del Día</span>
                <span className="px-2 py-1 rounded bg-amber-500/10 text-amber-300 text-xs font-mono font-bold flex items-center border border-amber-500/20">
                  <Zap className="w-3.5 h-3.5 mr-1" fill="currentColor" />
                  +74% Confianza
                </span>
              </div>
              <div className="flex items-center justify-between mb-6">
                <div className="text-center flex-1">
                  <div className="w-12 h-12 rounded-full bg-white/[0.06] mx-auto flex items-center justify-center mb-2">
                    <span className="font-mono font-bold text-white text-xs">ARS</span>
                  </div>
                  <div className="font-bold text-white text-lg">ARS</div>
                </div>
                <div className="text-zinc-500 font-mono text-sm">vs</div>
                <div className="text-center flex-1">
                  <div className="w-12 h-12 rounded-full bg-white/[0.06] mx-auto flex items-center justify-center mb-2">
                    <span className="font-mono font-bold text-white text-xs">CHE</span>
                  </div>
                  <div className="font-bold text-white text-lg">CHE</div>
                </div>
              </div>
              <div className="bg-white/[0.02] rounded-xl p-4 mb-4 border border-white/[0.04]">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-zinc-400">Mercado Recomendado</span>
                  <span className="text-white font-mono font-bold">Over 2.5 Goles</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-zinc-400">Cuota Algorítmica</span>
                  <span className="text-amber-400 font-mono font-bold">1.85</span>
                </div>
              </div>
              <div className="space-y-3">
                <div className="text-xs text-zinc-500 uppercase tracking-wider font-bold mb-2">Razonamiento IA</div>
                <div className="flex items-start space-x-3 text-sm text-zinc-300">
                  <CheckCircle2 className="w-[18px] h-[18px] mt-0.5 text-amber-500 flex-shrink-0" />
                  <span>Divergencia del 8% detectada frente a Pinnacle closing lines.</span>
                </div>
                <div className="flex items-start space-x-3 text-sm text-zinc-300">
                  <CheckCircle2 className="w-[18px] h-[18px] mt-0.5 text-amber-500 flex-shrink-0" />
                  <span>Modelo xG proyecta 3.12 goles esperados basados en ausencias defensivas.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 3: Cómo funciona — pipeline visual */}
      <section
        id="como-funciona"
        className="py-24 px-6 lg:px-8 bg-[#0a0a0c] border-y border-white/[0.06] scroll-mt-20 relative overflow-hidden"
      >
        <div
          className="absolute -top-40 left-1/2 -translate-x-1/2 w-[1100px] h-[600px] rounded-full pointer-events-none opacity-50"
          style={{
            background:
              'radial-gradient(circle, rgba(251,191,36,0.10) 0%, rgba(251,191,36,0) 60%)',
          }}
        />
        <div className="max-w-7xl mx-auto relative">
          <div className="text-center mb-14 max-w-2xl mx-auto">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 font-mono text-[10px] uppercase tracking-widest font-bold mb-5">
              <ShieldCheck className="w-3 h-3" />
              Cómo funciona
            </div>
            <h2 className="font-sans font-extrabold text-[28px] md:text-[40px] text-white tracking-tight leading-[1.05] mb-4">
              Pipeline cuantitativo, no <span className="text-amber-300">corazonadas</span>.
            </h2>
            <p className="font-sans text-[15px] text-zinc-400">
              Tres etapas. Cada pick pasa por las tres antes de aparecer en tu dashboard.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <PipelineStep
              step="01"
              icon={<Activity className="w-5 h-5" />}
              title="Ingesta de datos"
              desc="Cuotas Pinnacle/bookies + probabilidades Polymarket + 10+ años de resultados Football-Data."
              tags={['Pinnacle', 'Polymarket', 'Football-Data']}
            />
            <PipelineStep
              step="02"
              icon={<Brain className="w-5 h-5" />}
              title="Modelo ML"
              desc="Ensemble (XGBoost + Logistic) con TimeSeriesSplit. Features: forma, xG, ELO, h2h, gestión de riesgo."
              tags={['XGBoost', 'TimeSeriesSplit', 'Brier', 'Calibrated']}
              accent
            />
            <PipelineStep
              step="03"
              icon={<LineChart className="w-5 h-5" />}
              title="Detección de edge"
              desc="Comparamos prob. del modelo vs implícita de la cuota. Solo publicamos picks con edge ≥ 3%."
              tags={['Edge ≥ 3%', 'Kelly', 'Verificado']}
            />
          </div>

          <div className="mt-14 grid grid-cols-2 md:grid-cols-4 gap-4">
            <KpiTile label="Accuracy 30d" value="61.4%" tone="amber" />
            <KpiTile label="ROI mensual" value="+24.8%" tone="emerald" />
            <KpiTile label="Picks auditados" value="847" />
            <KpiTile label="Divergencias hoy" value="8" pulse />
          </div>
        </div>
      </section>

      {/* Section 4: Picks del día */}
      <section id="picks-dia" className="py-24 px-8 bg-background scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="text-3xl font-bold text-on-surface tracking-tight">Picks del Día</h2>
              <p className="text-tertiary mt-2">Señales algorítmicas con ventaja matemática detectada.</p>
            </div>
            <Link href={primaryCtaHref} className="text-amber-600 dark:text-amber-500 font-medium hover:text-amber-500 dark:hover:text-amber-400 transition-colors hidden sm:flex items-center">
              Ver todos
              <ArrowRight className="ml-1 w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-surface-container-lowest border border-surface-container-low rounded-2xl p-6 relative flex flex-col">
              <div className="absolute top-4 right-4 bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 px-2 py-1 rounded-full text-xs font-bold font-mono">FREE</div>
              <div className="flex items-center space-x-3 mb-6 pt-2">
                <Target className="w-5 h-5 text-tertiary" />
                <span className="text-sm font-medium text-tertiary">Premier League · 15:00 UTC</span>
              </div>
              <div className="flex justify-between items-center mb-6">
                <div className="font-bold text-lg">ARS</div>
                <div className="text-tertiary font-mono text-xs">vs</div>
                <div className="font-bold text-lg">CHE</div>
              </div>
              <div className="mt-auto bg-surface p-4 rounded-xl">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-on-surface-variant">Over 2.5 Goles</span>
                  <span className="font-mono font-bold text-on-surface">1.85</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-tertiary">Edge Detectado</span>
                  <span className="font-mono text-amber-500 font-bold text-xs">+4.2%</span>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-lowest border border-surface-container-low rounded-2xl p-6 relative flex flex-col">
              <div className="absolute top-4 right-4 bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 px-2 py-1 rounded-full text-xs font-bold font-mono">FREE</div>
              <div className="flex items-center space-x-3 mb-6 pt-2">
                <Target className="w-5 h-5 text-tertiary" />
                <span className="text-sm font-medium text-tertiary">La Liga · 19:00 UTC</span>
              </div>
              <div className="flex justify-between items-center mb-6">
                <div className="font-bold text-lg">RMA</div>
                <div className="text-tertiary font-mono text-xs">vs</div>
                <div className="font-bold text-lg">GET</div>
              </div>
              <div className="mt-auto bg-surface p-4 rounded-xl">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-on-surface-variant">RMA -1.5 (AH)</span>
                  <span className="font-mono font-bold text-on-surface">2.10</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-tertiary">Edge Detectado</span>
                  <span className="font-mono text-amber-500 font-bold text-xs">+3.8%</span>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-lowest border border-outline-variant/30 rounded-2xl p-6 relative flex flex-col overflow-hidden group">
              <div className="absolute inset-0 bg-surface-container-lowest/80 backdrop-blur-[4px] z-10 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-12 h-12 bg-amber-500/10 rounded-full flex items-center justify-center mb-3">
                  <Lock className="w-5 h-5 text-amber-500" />
                </div>
                <div className="font-bold mb-1 text-on-surface">Premium Pick</div>
                <div className="text-xs text-tertiary mb-4">Edge superior al 8% detectado</div>
                <Link href="/pricing" className="bg-amber-400 text-black rounded-full px-4 py-2 text-sm font-bold w-full hover:bg-amber-500 transition-colors">Desbloquear</Link>
              </div>

              <div className="opacity-50 blur-[2px] pointer-events-none select-none">
                <div className="flex items-center space-x-3 mb-6 pt-2">
                  <Target className="w-5 h-5 text-tertiary" />
                  <span className="text-sm font-medium text-tertiary">Bundesliga · 14:30 UTC</span>
                </div>
                <div className="flex justify-between items-center mb-6">
                  <div className="font-bold text-lg">BAY</div>
                  <div className="text-tertiary font-mono text-xs">vs</div>
                  <div className="font-bold text-lg">DOR</div>
                </div>
                <div className="mt-auto bg-surface p-4 rounded-xl">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-on-surface-variant">BAY Win to Nil</span>
                    <span className="font-mono font-bold text-on-surface">3.40</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-tertiary">Edge Detectado</span>
                    <span className="font-mono text-amber-500 font-bold text-xs">+9.2%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer id="comunidad" className="w-full pt-16 pb-8 bg-slate-50 dark:bg-[#0a0a0c] border-t border-slate-200 dark:border-white/[0.06] transition-all duration-300 scroll-mt-20">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-12 px-8 max-w-7xl mx-auto">
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="text-xl font-bold text-slate-900 dark:text-white flex items-center space-x-2 mb-4">
              <svg className="text-amber-500 dark:text-amber-400" fill="none" height="20" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" viewBox="0 0 24 24" width="20">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
              </svg>
              <span>Edgebet</span>
            </Link>
            <p className="text-slate-500 dark:text-zinc-400 text-sm mb-6 max-w-xs">The Quantitative Architect. Institutional-grade analytics for football markets.</p>
          </div>
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-sm mb-4 tracking-wider uppercase">Plataforma</h3>
            <ul className="space-y-3 text-sm">
              <li><Link href="#como-funciona" className="text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 transition-all">Cómo funciona</Link></li>
              <li><Link href="#picks-dia" className="text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 transition-all">Picks del día</Link></li>
              <li><Link href="/pricing" className="text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 transition-all">Precios</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-sm mb-4 tracking-wider uppercase">Cuenta</h3>
            <ul className="space-y-3 text-sm">
              <li><Link href={isAuthenticated ? '/dashboard' : '/login'} className="text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 transition-all">{isAuthenticated ? 'Dashboard' : 'Iniciar sesión'}</Link></li>
              <li><Link href={isAuthenticated ? '/dashboard/history' : '/register'} className="text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 transition-all">{isAuthenticated ? 'Historial' : 'Crear cuenta'}</Link></li>
              <li><Link href="/pricing" className="text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 transition-all">Planes</Link></li>
            </ul>
          </div>
          <div className="col-span-2 md:col-span-4 mt-8 pt-8 border-t border-slate-200 dark:border-white/[0.06]">
            <p className="text-slate-500 dark:text-zinc-500 text-sm text-center">© 2026 Edgebet. The Quantitative Architect.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function NavLink({
  href,
  label,
  active = false,
}: {
  href: string;
  label: string;
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`relative px-3.5 h-[40px] flex items-center font-sans text-[13px] font-semibold tracking-tight transition-colors ${
        active ? 'text-amber-300' : 'text-zinc-400 hover:text-white'
      }`}
    >
      {label}
      {active && (
        <span className="absolute -bottom-[1px] left-3 right-3 h-[2px] rounded-full bg-amber-300" />
      )}
    </Link>
  );
}

function PipelineStep({
  step,
  icon,
  title,
  desc,
  tags,
  accent = false,
}: {
  step: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
  tags: string[];
  accent?: boolean;
}) {
  return (
    <div
      className={`relative rounded-2xl border p-6 ${
        accent
          ? 'border-amber-500/20 bg-gradient-to-b from-amber-500/[0.06] to-[#111114]'
          : 'border-white/[0.08] bg-[#111114]'
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <div
          className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            accent ? 'bg-amber-400/20 text-amber-300' : 'bg-white/[0.06] text-zinc-300'
          }`}
        >
          {icon}
        </div>
        <span className="font-mono text-[11px] uppercase tracking-widest text-zinc-600 font-bold">
          {step}
        </span>
      </div>
      <h3 className="font-sans font-bold text-[18px] text-white mb-2 tracking-tight">{title}</h3>
      <p className="font-sans text-[13px] text-zinc-400 leading-relaxed mb-4">{desc}</p>
      <div className="flex flex-wrap gap-1.5">
        {tags.map((t) => (
          <span
            key={t}
            className="font-mono text-[10px] px-2 py-1 rounded-md bg-white/[0.04] text-zinc-400 border border-white/[0.06]"
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}

function KpiTile({
  label,
  value,
  tone,
  pulse = false,
}: {
  label: string;
  value: string;
  tone?: 'amber' | 'emerald';
  pulse?: boolean;
}) {
  const valueClass =
    tone === 'amber' ? 'text-amber-300' : tone === 'emerald' ? 'text-emerald-400' : 'text-white';
  return (
    <div className="bg-[#111114] border border-white/[0.06] rounded-xl p-5">
      <div className="flex items-center gap-2 mb-2">
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500 font-semibold">
          {label}
        </span>
        {pulse && (
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
        )}
      </div>
      <div className={`font-mono font-extrabold text-[28px] tracking-tight ${valueClass}`}>
        {value}
      </div>
    </div>
  );
}
