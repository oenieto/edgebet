'use client';

import Link from 'next/link';
import Image from 'next/image';
import { ArrowRight, Zap, CheckCircle2, TrendingUp, Target, Lock, LogOut, Shield, Flame } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function HomePage() {
  const { user, isAuthenticated, isHydrated, logout } = useAuth();
  const primaryCtaHref = isAuthenticated ? '/dashboard' : '/register';
  const primaryCtaLabel = isAuthenticated ? 'Ir al dashboard' : 'Empezar gratis';

  return (
    <div className="min-h-screen bg-background text-on-surface selection:bg-amber-500/30 selection:text-amber-900">
      {/* Section 1: Sticky Navbar */}
      <nav className="bg-white/80 dark:bg-[#0a0a0c]/80 backdrop-blur-md sticky top-0 z-50 w-full shadow-sm">
        <div className="flex items-center justify-between px-8 py-4 max-w-7xl mx-auto">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center">
              <Image
                src="/inverso.png"
                alt="Edgebet"
                width={160}
                height={40}
                priority
                className="h-[36px] w-auto object-cover"
                style={{ clipPath: 'inset(0px 0px 10px 0px)' }}
              />
            </Link>
            <div className="hidden md:flex space-x-6">
              <Link href="#como-funciona" className="text-slate-600 dark:text-slate-400 font-medium hover:text-amber-500 transition-colors duration-200">Cómo funciona</Link>
              <Link href="#picks-dia" className="text-amber-600 dark:text-amber-400 font-semibold border-b-2 border-amber-500 hover:text-amber-500 transition-colors duration-200 pb-1">Picks del día</Link>
              <Link href={isAuthenticated ? '/dashboard/history' : '/login'} className="text-slate-600 dark:text-slate-400 font-medium hover:text-amber-500 transition-colors duration-200">Historial</Link>
              <Link href="/pricing" className="text-slate-600 dark:text-slate-400 font-medium hover:text-amber-500 transition-colors duration-200">Precios</Link>
              <Link href="#comunidad" className="text-slate-600 dark:text-slate-400 font-medium hover:text-amber-500 transition-colors duration-200">Comunidad</Link>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {isHydrated && isAuthenticated && user ? (
              <>
                <span className="hidden md:inline-flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                  <span className="w-7 h-7 rounded-full bg-amber-500/10 text-amber-500 flex items-center justify-center font-mono text-xs font-bold">
                    {user.name.charAt(0).toUpperCase()}
                  </span>
                  {user.name}
                </span>
                <Link
                  href="/dashboard"
                  className="bg-amber-400 text-black rounded-full px-6 py-2.5 font-bold hover:bg-amber-500 transition-colors shadow-sm"
                >
                  Dashboard
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  aria-label="Cerrar sesión"
                  className="text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-slate-600 dark:text-slate-400 font-medium hover:text-amber-500 transition-colors duration-200 hidden md:block"
                >
                  Iniciar sesión
                </Link>
                <Link
                  href={primaryCtaHref}
                  className="bg-amber-400 text-black rounded-full px-6 py-2.5 font-bold hover:bg-amber-500 transition-colors shadow-sm"
                >
                  {primaryCtaLabel}
                </Link>
              </>
            )}
          </div>
        </div>
        <div className="bg-slate-100 dark:bg-zinc-800/50 h-[1px] w-full"></div>
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

      {/* Section 3: Métricas */}
      <section id="como-funciona" className="py-20 px-8 bg-surface border-b border-surface-container-high scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-low relative overflow-hidden transition-all hover:bg-surface-container-low group">
              <div className="text-sm text-tertiary font-medium mb-2">Accuracy (30d)</div>
              <div className="flex items-end justify-between">
                <div className="text-3xl font-bold font-mono text-on-surface">61.4%</div>
                <div className="h-8 w-24 bg-surface-container-high rounded flex items-end overflow-hidden">
                  <div className="w-1/6 bg-amber-500/40 h-[40%] ml-[2px]"></div>
                  <div className="w-1/6 bg-amber-500/50 h-[50%] ml-[2px]"></div>
                  <div className="w-1/6 bg-amber-500/70 h-[80%] ml-[2px]"></div>
                  <div className="w-1/6 bg-error/40 h-[30%] ml-[2px]"></div>
                  <div className="w-1/6 bg-amber-500/80 h-[90%] ml-[2px]"></div>
                  <div className="w-1/6 bg-amber-500 h-[100%] ml-[2px]"></div>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-low transition-all hover:bg-surface-container-low">
              <div className="text-sm text-tertiary font-medium mb-2">ROI Mensual</div>
              <div className="text-3xl font-bold font-mono text-amber-500 flex items-center">
                <TrendingUp className="w-6 h-6 mr-1" />
                +24.8%
              </div>
            </div>

            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-low transition-all hover:bg-surface-container-low">
              <div className="text-sm text-tertiary font-medium mb-2">Picks Verificados</div>
              <div className="text-3xl font-bold font-mono text-on-surface">847</div>
            </div>

            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-low transition-all hover:bg-surface-container-low">
              <div className="text-sm text-tertiary font-medium mb-2 flex items-center">
                Divergencias Activas
                <span className="w-2 h-2 rounded-full bg-amber-500 ml-2 animate-pulse"></span>
              </div>
              <div className="text-3xl font-bold font-mono text-amber-500">8 hoy</div>
            </div>
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

      {/* Section 5: Parlays Recomendados */}
      <section id="parlays-recomendados" className="py-24 px-8 bg-surface-container-lowest border-t border-surface-container-low scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="text-3xl font-bold text-on-surface tracking-tight">Parlays Recomendados</h2>
              <p className="text-tertiary mt-2">Combinaciones de picks del día optimizadas por nivel de riesgo.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Parlay Seguro */}
            <div className="bg-surface border border-surface-container-low rounded-2xl p-6 relative flex flex-col hover:border-amber-500/50 transition-colors">
              <div className="absolute top-4 right-4 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full text-xs font-bold font-mono flex items-center">
                <Shield className="w-3.5 h-3.5 mr-1" />
                SEGURO
              </div>
              <div className="mb-6 pt-2">
                <h3 className="font-bold text-xl text-on-surface">Double Seguro</h3>
                <p className="text-sm text-tertiary mt-1">Nuestra combinación más conservadora.</p>
              </div>
              
              <div className="space-y-4 mb-6 flex-1">
                <div className="bg-surface-container-lowest p-3 rounded-lg border border-surface-container-low">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-bold text-on-surface">ARS vs CHE</span>
                    <span className="font-mono text-on-surface">1.85</span>
                  </div>
                  <div className="text-xs text-tertiary">Over 2.5 Goles</div>
                </div>
                <div className="bg-surface-container-lowest p-3 rounded-lg border border-surface-container-low">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-bold text-on-surface">RMA vs GET</span>
                    <span className="font-mono text-on-surface">2.10</span>
                  </div>
                  <div className="text-xs text-tertiary">RMA -1.5 (AH)</div>
                </div>
              </div>

              <div className="mt-auto bg-amber-500/5 p-4 rounded-xl border border-amber-500/20">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-bold text-on-surface">Cuota Total</span>
                  <span className="font-mono text-amber-500 font-bold text-xl">3.88</span>
                </div>
              </div>
            </div>

            {/* Parlay Intermedio (Premium) */}
            <div className="bg-surface border border-outline-variant/30 rounded-2xl p-6 relative flex flex-col overflow-hidden group">
              <div className="absolute inset-0 bg-surface/80 backdrop-blur-[4px] z-10 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-12 h-12 bg-amber-500/10 rounded-full flex items-center justify-center mb-3">
                  <Lock className="w-5 h-5 text-amber-500" />
                </div>
                <div className="font-bold mb-1 text-on-surface">Parlay Intermedio</div>
                <div className="text-xs text-tertiary mb-4">Incluye picks premium con alto valor</div>
                <Link href="/pricing" className="bg-amber-400 text-black rounded-full px-4 py-2 text-sm font-bold w-full hover:bg-amber-500 transition-colors">Desbloquear</Link>
              </div>

              <div className="opacity-50 blur-[2px] pointer-events-none select-none flex-1 flex flex-col">
                <div className="absolute top-4 right-4 bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 px-3 py-1 rounded-full text-xs font-bold font-mono flex items-center">
                  <TrendingUp className="w-3.5 h-3.5 mr-1" />
                  MEDIO
                </div>
                <div className="mb-6 pt-2">
                  <h3 className="font-bold text-xl text-on-surface">Double Valor</h3>
                  <p className="text-sm text-tertiary mt-1">Equilibrio entre riesgo y recompensa.</p>
                </div>
                
                <div className="space-y-4 mb-6 flex-1">
                  <div className="bg-surface-container-lowest p-3 rounded-lg border border-surface-container-low">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-bold text-on-surface">RMA vs GET</span>
                      <span className="font-mono text-on-surface">2.10</span>
                    </div>
                    <div className="text-xs text-tertiary">RMA -1.5 (AH)</div>
                  </div>
                  <div className="bg-surface-container-lowest p-3 rounded-lg border border-surface-container-low">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-bold text-on-surface">BAY vs DOR</span>
                      <span className="font-mono text-on-surface">3.40</span>
                    </div>
                    <div className="text-xs text-tertiary">BAY Win to Nil</div>
                  </div>
                </div>

                <div className="mt-auto bg-amber-500/5 p-4 rounded-xl border border-amber-500/20">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-bold text-on-surface">Cuota Total</span>
                    <span className="font-mono text-amber-500 font-bold text-xl">7.14</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Parlay Arriesgado (Premium) */}
            <div className="bg-surface border border-outline-variant/30 rounded-2xl p-6 relative flex flex-col overflow-hidden group">
              <div className="absolute inset-0 bg-surface/80 backdrop-blur-[4px] z-10 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-12 h-12 bg-amber-500/10 rounded-full flex items-center justify-center mb-3">
                  <Lock className="w-5 h-5 text-amber-500" />
                </div>
                <div className="font-bold mb-1 text-on-surface">Parlay Arriesgado</div>
                <div className="text-xs text-tertiary mb-4">La combinada completa del día</div>
                <Link href="/pricing" className="bg-amber-400 text-black rounded-full px-4 py-2 text-sm font-bold w-full hover:bg-amber-500 transition-colors">Desbloquear</Link>
              </div>

              <div className="opacity-50 blur-[2px] pointer-events-none select-none flex-1 flex flex-col">
                <div className="absolute top-4 right-4 bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 px-3 py-1 rounded-full text-xs font-bold font-mono flex items-center">
                  <Flame className="w-3.5 h-3.5 mr-1" />
                  RIESGO
                </div>
                <div className="mb-6 pt-2">
                  <h3 className="font-bold text-xl text-on-surface">Lotto Treble</h3>
                  <p className="text-sm text-tertiary mt-1">Máxima cuota, ideal para stakes bajos.</p>
                </div>
                
                <div className="space-y-4 mb-6 flex-1">
                  <div className="bg-surface-container-lowest p-3 rounded-lg border border-surface-container-low">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-bold text-on-surface">ARS vs CHE</span>
                      <span className="font-mono text-on-surface">1.85</span>
                    </div>
                  </div>
                  <div className="bg-surface-container-lowest p-3 rounded-lg border border-surface-container-low">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-bold text-on-surface">RMA vs GET</span>
                      <span className="font-mono text-on-surface">2.10</span>
                    </div>
                  </div>
                  <div className="bg-surface-container-lowest p-3 rounded-lg border border-surface-container-low">
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-bold text-on-surface">BAY vs DOR</span>
                      <span className="font-mono text-on-surface">3.40</span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto bg-amber-500/5 p-4 rounded-xl border border-amber-500/20">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-bold text-on-surface">Cuota Total</span>
                    <span className="font-mono text-amber-500 font-bold text-xl">13.21</span>
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
