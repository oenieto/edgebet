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
    <div className="min-h-screen bg-background text-on-surface">
      {/* Section 1: Sticky Navbar */}
      <nav className="bg-surface/90 backdrop-blur-md sticky top-0 z-50 w-full border-b border-surface-container-high">
        <div className="flex items-center justify-between px-8 py-4 max-w-7xl mx-auto">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-primary" />
              <span className="font-sans font-bold text-[20px] tracking-tight text-on-surface">
                Edge<span className="font-normal text-tertiary">bet</span>
              </span>
            </Link>
            <div className="hidden md:flex space-x-6">
              <Link href="#como-funciona" className="text-[14px] text-on-surface-variant font-medium hover:text-primary transition-colors">Cómo funciona</Link>
              <Link href="#picks-dia" className="text-[14px] text-primary font-semibold hover:opacity-80 transition-colors">Picks del día</Link>
              <Link href={isAuthenticated ? '/dashboard/history' : '/login'} className="text-[14px] text-on-surface-variant font-medium hover:text-primary transition-colors">Historial</Link>
              <Link href="/pricing" className="text-[14px] text-on-surface-variant font-medium hover:text-primary transition-colors">Precios</Link>
              <Link href="#comunidad" className="text-[14px] text-on-surface-variant font-medium hover:text-primary transition-colors">Comunidad</Link>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            {isHydrated && isAuthenticated && user ? (
              <>
                <span className="hidden md:inline-flex items-center gap-2 text-[14px] font-medium text-on-surface-variant">
                  <span className="w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center font-mono text-[12px] font-bold">
                    {user.name.charAt(0).toUpperCase()}
                  </span>
                  {user.name}
                </span>
                <Link
                  href="/dashboard"
                  className="bg-primary text-white rounded-full px-5 py-2.5 text-[14px] font-bold hover:opacity-90 transition-opacity"
                >
                  Dashboard
                </Link>
                <button
                  type="button"
                  onClick={logout}
                  aria-label="Cerrar sesión"
                  className="text-tertiary hover:text-on-surface transition-colors"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-[14px] text-on-surface-variant font-medium hover:text-primary transition-colors hidden md:block"
                >
                  Iniciar sesión
                </Link>
                <Link
                  href={primaryCtaHref}
                  className="bg-primary text-white rounded-full px-5 py-2.5 text-[14px] font-bold hover:opacity-90 transition-opacity"
                >
                  {primaryCtaLabel}
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Section 2: Hero */}
      <section className="bg-surface-container-lowest pt-24 pb-32 px-8 overflow-hidden relative border-b border-surface-container-high">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16 relative z-10 items-center">
          <div className="space-y-8">
            <div className="inline-flex items-center px-4 py-1.5 rounded-full border border-primary/20 bg-primary/5 text-primary text-[13px] font-medium font-mono mb-4">
              <span className="w-2 h-2 rounded-full bg-primary mr-2 animate-pulse"></span>
              IA · Polymarket · Pinnacle API
            </div>
            <h1 className="text-[48px] lg:text-[64px] font-extrabold leading-tight tracking-tight text-on-surface">
              El <span className="text-primary">edge</span> que los tipsters no tienen.
            </h1>
            <p className="text-[18px] text-tertiary max-w-lg leading-relaxed">
              Arquitectura cuantitativa para el mercado de fútbol. Detectamos divergencias de probabilidad en tiempo real cruzando datos de exchanges predictivos y casas de apuestas institucionales.
            </p>
            <div className="flex items-center space-x-4 pt-4">
              <Link href={primaryCtaHref} className="bg-primary text-white rounded-full px-8 py-4 font-bold text-[16px] hover:opacity-90 transition-opacity flex items-center">
                {isAuthenticated ? 'Ir al dashboard' : 'Ver picks abiertos'}
                <ArrowRight className="ml-2 w-5 h-5" />
              </Link>
            </div>
            <div className="flex items-center space-x-8 pt-8 border-t border-surface-container-high mt-8">
              <div>
                <div className="font-mono text-[24px] font-bold text-on-surface">6</div>
                <div className="text-[11px] text-tertiary mt-1 uppercase tracking-widest">Ligas Modeladas</div>
              </div>
              <div className="w-px h-10 bg-surface-container-high"></div>
              <div>
                <div className="font-mono text-[24px] font-bold text-on-surface">ELO + Poisson</div>
                <div className="text-[11px] text-tertiary mt-1 uppercase tracking-widest">Motor estadístico</div>
              </div>
              <div className="w-px h-10 bg-surface-container-high"></div>
              <div>
                <div className="font-mono text-[24px] font-bold text-on-surface">6 mercados</div>
                <div className="text-[11px] text-tertiary mt-1 uppercase tracking-widest">1X2 · DC · OU · BTTS · Spread · TT</div>
              </div>
            </div>
          </div>

          <div className="relative lg:ml-auto w-full max-w-md">
            <div className="bg-background border border-surface-container-high rounded-[24px] p-6 shadow-xl relative z-10">
              <div className="flex justify-between items-center mb-6">
                <span className="text-[12px] font-bold text-tertiary tracking-wider uppercase">Pick Del Día</span>
                <span className="px-2.5 py-1 rounded-md bg-secondary-container text-on-secondary-container text-[12px] font-mono font-bold flex items-center">
                  <Zap className="w-3.5 h-3.5 mr-1" fill="currentColor" />
                  +74% Confianza
                </span>
              </div>
              <div className="flex items-center justify-between mb-6">
                <div className="text-center flex-1">
                  <div className="w-12 h-12 rounded-full bg-surface-container-high mx-auto flex items-center justify-center mb-2">
                    <span className="font-mono font-bold text-on-surface text-[13px]">ARS</span>
                  </div>
                  <div className="font-bold text-on-surface text-[18px]">ARS</div>
                </div>
                <div className="text-tertiary font-mono text-[14px]">vs</div>
                <div className="text-center flex-1">
                  <div className="w-12 h-12 rounded-full bg-surface-container-high mx-auto flex items-center justify-center mb-2">
                    <span className="font-mono font-bold text-on-surface text-[13px]">CHE</span>
                  </div>
                  <div className="font-bold text-on-surface text-[18px]">CHE</div>
                </div>
              </div>
              <div className="bg-surface rounded-xl p-4 mb-4 border border-surface-container-low">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[14px] text-on-surface-variant">Mercado Recomendado</span>
                  <span className="text-on-surface font-mono font-bold">Over 2.5 Goles</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[14px] text-on-surface-variant">Cuota Algorítmica</span>
                  <span className="text-primary font-mono font-bold">1.85</span>
                </div>
              </div>
              <div className="space-y-3">
                <div className="text-[12px] text-tertiary uppercase tracking-wider font-bold mb-2">Razonamiento IA</div>
                <div className="flex items-start space-x-3 text-[14px] text-on-surface-variant">
                  <CheckCircle2 className="w-[18px] h-[18px] mt-0.5 text-secondary flex-shrink-0" />
                  <span>Divergencia del 8% detectada frente a Pinnacle closing lines.</span>
                </div>
                <div className="flex items-start space-x-3 text-[14px] text-on-surface-variant">
                  <CheckCircle2 className="w-[18px] h-[18px] mt-0.5 text-secondary flex-shrink-0" />
                  <span>Modelo xG proyecta 3.12 goles esperados basados en ausencias defensivas.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 3: Métricas */}
      <section id="como-funciona" className="py-20 px-8 bg-background border-b border-surface-container-high scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-low relative overflow-hidden transition-all hover:border-outline-variant">
              <div className="text-[14px] text-tertiary font-medium mb-2">Accuracy (30d)</div>
              <div className="flex items-end justify-between">
                <div className="text-[32px] font-bold font-mono text-on-surface leading-none">—</div>
                <div className="h-6 px-2 bg-surface-container-high rounded flex items-center justify-center">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-tertiary">en construcción</span>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-low transition-all hover:border-outline-variant">
              <div className="text-[14px] text-tertiary font-medium mb-2">ROI Mensual</div>
              <div className="text-[32px] font-bold font-mono text-secondary flex items-center leading-none">
                <TrendingUp className="w-6 h-6 mr-2" />
                +24.8%
              </div>
            </div>

            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-low transition-all hover:border-outline-variant">
              <div className="text-[14px] text-tertiary font-medium mb-2">Picks Verificados</div>
              <div className="text-[32px] font-bold font-mono text-on-surface leading-none">847</div>
            </div>

            <div className="bg-surface-container-lowest p-6 rounded-2xl border border-surface-container-low transition-all hover:border-outline-variant">
              <div className="text-[14px] text-tertiary font-medium mb-2 flex items-center">
                Divergencias Activas
                <span className="w-2 h-2 rounded-full bg-warning ml-2 animate-pulse"></span>
              </div>
              <div className="text-[32px] font-bold font-mono text-warning leading-none">8 hoy</div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 4: Picks del día */}
      <section id="picks-dia" className="py-24 px-8 bg-surface scroll-mt-20 border-b border-surface-container-high">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="text-[32px] font-bold text-on-surface tracking-tight">Picks del Día</h2>
              <p className="text-[16px] text-tertiary mt-2">Señales algorítmicas con ventaja matemática detectada.</p>
            </div>
            <Link href={primaryCtaHref} className="text-primary font-medium hover:underline transition-all hidden sm:flex items-center">
              Ver todos
              <ArrowRight className="ml-1 w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-surface-container-lowest border border-surface-container-low rounded-[24px] p-6 relative flex flex-col">
              <div className="absolute top-5 right-5 bg-secondary/10 text-secondary border border-secondary/20 px-2.5 py-1 rounded-md text-[11px] font-bold font-mono">FREE</div>
              <div className="flex items-center space-x-3 mb-6 pt-1">
                <Target className="w-5 h-5 text-tertiary" />
                <span className="text-[13px] font-medium text-tertiary">Premier League · 15:00 UTC</span>
              </div>
              <div className="flex justify-between items-center mb-6">
                <div className="font-bold text-[20px] text-on-surface">ARS</div>
                <div className="text-tertiary font-mono text-[13px]">vs</div>
                <div className="font-bold text-[20px] text-on-surface">CHE</div>
              </div>
              <div className="mt-auto bg-background p-4 rounded-xl border border-surface-container-low">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[14px] text-on-surface-variant">Over 2.5 Goles</span>
                  <span className="font-mono font-bold text-on-surface">1.85</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[12px] text-tertiary uppercase tracking-wider font-bold">Edge Detectado</span>
                  <span className="font-mono text-secondary font-bold text-[14px]">+4.2%</span>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-lowest border border-surface-container-low rounded-[24px] p-6 relative flex flex-col">
              <div className="absolute top-5 right-5 bg-secondary/10 text-secondary border border-secondary/20 px-2.5 py-1 rounded-md text-[11px] font-bold font-mono">FREE</div>
              <div className="flex items-center space-x-3 mb-6 pt-1">
                <Target className="w-5 h-5 text-tertiary" />
                <span className="text-[13px] font-medium text-tertiary">La Liga · 19:00 UTC</span>
              </div>
              <div className="flex justify-between items-center mb-6">
                <div className="font-bold text-[20px] text-on-surface">RMA</div>
                <div className="text-tertiary font-mono text-[13px]">vs</div>
                <div className="font-bold text-[20px] text-on-surface">GET</div>
              </div>
              <div className="mt-auto bg-background p-4 rounded-xl border border-surface-container-low">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[14px] text-on-surface-variant">RMA -1.5 (AH)</span>
                  <span className="font-mono font-bold text-on-surface">2.10</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[12px] text-tertiary uppercase tracking-wider font-bold">Edge Detectado</span>
                  <span className="font-mono text-secondary font-bold text-[14px]">+3.8%</span>
                </div>
              </div>
            </div>

            <div className="bg-surface-container-lowest border border-warning/30 rounded-[24px] p-6 relative flex flex-col overflow-hidden group">
              <div className="absolute inset-0 bg-surface-container-lowest/80 backdrop-blur-[6px] z-10 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-12 h-12 bg-warning/10 rounded-full flex items-center justify-center mb-3">
                  <Lock className="w-5 h-5 text-warning" />
                </div>
                <div className="font-bold mb-1 text-on-surface text-[16px]">Premium Pick</div>
                <div className="text-[13px] text-tertiary mb-4">Edge superior al 8% detectado</div>
                <Link href="/pricing" className="bg-warning text-white rounded-full px-5 py-2 text-[14px] font-bold w-full hover:opacity-90 transition-opacity">Desbloquear</Link>
              </div>

              <div className="opacity-40 blur-[2px] pointer-events-none select-none flex-1 flex flex-col">
                <div className="flex items-center space-x-3 mb-6 pt-1">
                  <Target className="w-5 h-5 text-tertiary" />
                  <span className="text-[13px] font-medium text-tertiary">Bundesliga · 14:30 UTC</span>
                </div>
                <div className="flex justify-between items-center mb-6">
                  <div className="font-bold text-[20px] text-on-surface">BAY</div>
                  <div className="text-tertiary font-mono text-[13px]">vs</div>
                  <div className="font-bold text-[20px] text-on-surface">DOR</div>
                </div>
                <div className="mt-auto bg-background p-4 rounded-xl border border-surface-container-low">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[14px] text-on-surface-variant">BAY Win to Nil</span>
                    <span className="font-mono font-bold text-on-surface">3.40</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[12px] text-tertiary uppercase tracking-wider font-bold">Edge Detectado</span>
                    <span className="font-mono text-warning font-bold text-[14px]">+9.2%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 5: Parlays Recomendados */}
      <section id="parlays-recomendados" className="py-24 px-8 bg-background scroll-mt-20">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="text-[32px] font-bold text-on-surface tracking-tight">Parlays Recomendados</h2>
              <p className="text-[16px] text-tertiary mt-2">Combinaciones de picks del día optimizadas por nivel de riesgo.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Parlay Seguro */}
            <div className="bg-surface-container-lowest border border-secondary/30 rounded-[24px] p-6 relative flex flex-col hover:border-secondary transition-colors">
              <div className="absolute top-5 right-5 bg-secondary/10 text-secondary border border-secondary/20 px-2.5 py-1 rounded-md text-[11px] font-bold font-mono flex items-center">
                <Shield className="w-3.5 h-3.5 mr-1" />
                SEGURO
              </div>
              <div className="mb-6 pt-1">
                <h3 className="font-bold text-[20px] text-on-surface">Double Seguro</h3>
                <p className="text-[13px] text-tertiary mt-1">Nuestra combinación más conservadora.</p>
              </div>
              
              <div className="space-y-3 mb-6 flex-1">
                <div className="bg-surface p-3.5 rounded-xl border border-surface-container-low">
                  <div className="flex justify-between text-[14px] mb-1">
                    <span className="font-bold text-on-surface">ARS vs CHE</span>
                    <span className="font-mono text-on-surface">1.85</span>
                  </div>
                  <div className="text-[13px] text-tertiary">Over 2.5 Goles</div>
                </div>
                <div className="bg-surface p-3.5 rounded-xl border border-surface-container-low">
                  <div className="flex justify-between text-[14px] mb-1">
                    <span className="font-bold text-on-surface">RMA vs GET</span>
                    <span className="font-mono text-on-surface">2.10</span>
                  </div>
                  <div className="text-[13px] text-tertiary">RMA -1.5 (AH)</div>
                </div>
              </div>

              <div className="mt-auto bg-secondary/5 p-4 rounded-xl border border-secondary/20">
                <div className="flex justify-between items-center">
                  <span className="text-[14px] font-bold text-on-surface">Cuota Total</span>
                  <span className="font-mono text-secondary font-bold text-[20px]">3.88</span>
                </div>
              </div>
            </div>

            {/* Parlay Intermedio (Premium) */}
            <div className="bg-surface-container-lowest border border-surface-container-high rounded-[24px] p-6 relative flex flex-col overflow-hidden group">
              <div className="absolute inset-0 bg-surface-container-lowest/80 backdrop-blur-[6px] z-10 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3">
                  <Lock className="w-5 h-5 text-primary" />
                </div>
                <div className="font-bold mb-1 text-on-surface text-[16px]">Parlay Intermedio</div>
                <div className="text-[13px] text-tertiary mb-4">Incluye picks premium con alto valor</div>
                <Link href="/pricing" className="bg-primary text-white rounded-full px-5 py-2 text-[14px] font-bold w-full hover:opacity-90 transition-opacity">Desbloquear</Link>
              </div>

              <div className="opacity-40 blur-[2px] pointer-events-none select-none flex-1 flex flex-col">
                <div className="absolute top-5 right-5 bg-primary/10 text-primary border border-primary/20 px-2.5 py-1 rounded-md text-[11px] font-bold font-mono flex items-center">
                  <TrendingUp className="w-3.5 h-3.5 mr-1" />
                  MEDIO
                </div>
                <div className="mb-6 pt-1">
                  <h3 className="font-bold text-[20px] text-on-surface">Double Valor</h3>
                  <p className="text-[13px] text-tertiary mt-1">Equilibrio entre riesgo y recompensa.</p>
                </div>
                
                <div className="space-y-3 mb-6 flex-1">
                  <div className="bg-surface p-3.5 rounded-xl border border-surface-container-low">
                    <div className="flex justify-between text-[14px] mb-1">
                      <span className="font-bold text-on-surface">RMA vs GET</span>
                      <span className="font-mono text-on-surface">2.10</span>
                    </div>
                    <div className="text-[13px] text-tertiary">RMA -1.5 (AH)</div>
                  </div>
                  <div className="bg-surface p-3.5 rounded-xl border border-surface-container-low">
                    <div className="flex justify-between text-[14px] mb-1">
                      <span className="font-bold text-on-surface">BAY vs DOR</span>
                      <span className="font-mono text-on-surface">3.40</span>
                    </div>
                    <div className="text-[13px] text-tertiary">BAY Win to Nil</div>
                  </div>
                </div>

                <div className="mt-auto bg-primary/5 p-4 rounded-xl border border-primary/20">
                  <div className="flex justify-between items-center">
                    <span className="text-[14px] font-bold text-on-surface">Cuota Total</span>
                    <span className="font-mono text-primary font-bold text-[20px]">7.14</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Parlay Arriesgado (Premium) */}
            <div className="bg-surface-container-lowest border border-surface-container-high rounded-[24px] p-6 relative flex flex-col overflow-hidden group">
              <div className="absolute inset-0 bg-surface-container-lowest/80 backdrop-blur-[6px] z-10 flex flex-col items-center justify-center p-6 text-center">
                <div className="w-12 h-12 bg-danger/10 rounded-full flex items-center justify-center mb-3">
                  <Lock className="w-5 h-5 text-danger" />
                </div>
                <div className="font-bold mb-1 text-on-surface text-[16px]">Parlay Arriesgado</div>
                <div className="text-[13px] text-tertiary mb-4">La combinada completa del día</div>
                <Link href="/pricing" className="bg-danger text-white rounded-full px-5 py-2 text-[14px] font-bold w-full hover:opacity-90 transition-opacity">Desbloquear</Link>
              </div>

              <div className="opacity-40 blur-[2px] pointer-events-none select-none flex-1 flex flex-col">
                <div className="absolute top-5 right-5 bg-danger/10 text-danger border border-danger/20 px-2.5 py-1 rounded-md text-[11px] font-bold font-mono flex items-center">
                  <Flame className="w-3.5 h-3.5 mr-1" />
                  RIESGO
                </div>
                <div className="mb-6 pt-1">
                  <h3 className="font-bold text-[20px] text-on-surface">Lotto Treble</h3>
                  <p className="text-[13px] text-tertiary mt-1">Máxima cuota, ideal para stakes bajos.</p>
                </div>
                
                <div className="space-y-3 mb-6 flex-1">
                  <div className="bg-surface p-3.5 rounded-xl border border-surface-container-low">
                    <div className="flex justify-between text-[14px] mb-1">
                      <span className="font-bold text-on-surface">ARS vs CHE</span>
                      <span className="font-mono text-on-surface">1.85</span>
                    </div>
                  </div>
                  <div className="bg-surface p-3.5 rounded-xl border border-surface-container-low">
                    <div className="flex justify-between text-[14px] mb-1">
                      <span className="font-bold text-on-surface">RMA vs GET</span>
                      <span className="font-mono text-on-surface">2.10</span>
                    </div>
                  </div>
                  <div className="bg-surface p-3.5 rounded-xl border border-surface-container-low">
                    <div className="flex justify-between text-[14px] mb-1">
                      <span className="font-bold text-on-surface">BAY vs DOR</span>
                      <span className="font-mono text-on-surface">3.40</span>
                    </div>
                  </div>
                </div>

                <div className="mt-auto bg-danger/5 p-4 rounded-xl border border-danger/20">
                  <div className="flex justify-between items-center">
                    <span className="text-[14px] font-bold text-on-surface">Cuota Total</span>
                    <span className="font-mono text-danger font-bold text-[20px]">13.21</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer id="comunidad" className="w-full pt-16 pb-8 bg-surface-container-lowest border-t border-surface-container-high scroll-mt-20">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-12 px-8 max-w-7xl mx-auto">
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="text-[20px] font-bold text-on-surface flex items-center space-x-2 mb-4">
              <TrendingUp className="text-primary w-6 h-6" />
              <span>Edge<span className="font-normal text-tertiary">bet</span></span>
            </Link>
            <p className="text-tertiary text-[13px] mb-6 max-w-xs leading-relaxed">The Quantitative Architect. Institutional-grade analytics for football markets.</p>
          </div>
          <div>
            <h3 className="font-bold text-on-surface text-[12px] mb-4 tracking-wider uppercase">Plataforma</h3>
            <ul className="space-y-3 text-[14px]">
              <li><Link href="#como-funciona" className="text-on-surface-variant hover:text-primary transition-colors">Cómo funciona</Link></li>
              <li><Link href="#picks-dia" className="text-on-surface-variant hover:text-primary transition-colors">Picks del día</Link></li>
              <li><Link href="/pricing" className="text-on-surface-variant hover:text-primary transition-colors">Precios</Link></li>
            </ul>
          </div>
          <div>
            <h3 className="font-bold text-on-surface text-[12px] mb-4 tracking-wider uppercase">Cuenta</h3>
            <ul className="space-y-3 text-[14px]">
              <li><Link href={isAuthenticated ? '/dashboard' : '/login'} className="text-on-surface-variant hover:text-primary transition-colors">{isAuthenticated ? 'Dashboard' : 'Iniciar sesión'}</Link></li>
              <li><Link href={isAuthenticated ? '/dashboard/history' : '/register'} className="text-on-surface-variant hover:text-primary transition-colors">{isAuthenticated ? 'Historial' : 'Crear cuenta'}</Link></li>
              <li><Link href="/pricing" className="text-on-surface-variant hover:text-primary transition-colors">Planes</Link></li>
            </ul>
          </div>
          <div className="col-span-2 md:col-span-4 mt-8 pt-8 border-t border-surface-container-high">
            <p className="text-tertiary text-[13px] text-center">© 2026 Edgebet. The Quantitative Architect.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
