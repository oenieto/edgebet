'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';

import { useAuth, ApiError } from '@/contexts/AuthContext';

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (loading) return;
    setError(null);

    if (password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres.');
      return;
    }

    setLoading(true);
    try {
      await register(email.trim(), password, name.trim());
      router.push('/dashboard');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || 'No se pudo crear la cuenta');
      } else {
        setError('No se pudo conectar con el servidor. ¿Está corriendo en :8000?');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex-grow flex flex-col md:flex-row h-screen overflow-hidden bg-white">
      <section
        aria-label="Registration"
        className="w-full md:w-1/2 flex flex-col justify-center items-center p-6 md:p-12 relative overflow-y-auto"
      >
        <div className="md:hidden absolute top-8 left-8">
          <Link href="/" className="flex items-center">
            <Image
              src="/logo.png"
              alt="Edgebet"
              width={160}
              height={40}
              priority
              className="h-[32px] w-auto object-cover"
              style={{ clipPath: 'inset(0px 0px 10px 0px)' }}
            />
          </Link>
        </div>
        <div className="w-full max-w-[400px] flex flex-col gap-6 mt-16 md:mt-0">
          <div className="space-y-2 text-center md:text-left">
            <h2 className="font-sans font-bold text-[28px] text-[#0a0a0c]">Crea tu cuenta</h2>
            <p className="font-sans text-[14px] text-slate-500">
              Accede al pick diario gratis. Sin tarjeta de crédito.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="font-sans text-[12px] font-medium text-slate-600 uppercase tracking-wide">
                Nombre
              </span>
              <input
                type="text"
                required
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Tu nombre"
                className="h-[44px] px-3 bg-white border border-slate-200 rounded-lg text-[14px] font-sans text-[#0a0a0c] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500 transition-all"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="font-sans text-[12px] font-medium text-slate-600 uppercase tracking-wide">
                Email
              </span>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="tu@email.com"
                className="h-[44px] px-3 bg-white border border-slate-200 rounded-lg text-[14px] font-sans text-[#0a0a0c] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500 transition-all"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="font-sans text-[12px] font-medium text-slate-600 uppercase tracking-wide">
                Contraseña
              </span>
              <input
                type="password"
                required
                autoComplete="new-password"
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Mínimo 6 caracteres"
                className="h-[44px] px-3 bg-white border border-slate-200 rounded-lg text-[14px] font-sans text-[#0a0a0c] placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500 transition-all"
              />
            </label>

            {error && (
              <div
                role="alert"
                className="px-3 py-2 bg-red-50 border border-red-100 rounded-lg text-[13px] font-sans text-red-700"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-[48px] bg-[#0a0a0c] hover:bg-zinc-800 transition-colors rounded-full flex items-center justify-center text-amber-300 font-sans font-semibold text-[15px] cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed mt-2 shadow-sm"
            >
              {loading ? 'Creando cuenta…' : 'Crear cuenta'}
            </button>
          </form>

          <div className="flex flex-col items-center gap-4 mt-2">
            <p className="font-sans text-[14px] text-slate-500">
              ¿Ya tienes cuenta?{' '}
              <Link className="text-amber-600 font-medium hover:underline" href="/login">
                Inicia sesión
              </Link>
            </p>
          </div>
        </div>
      </section>
      <section
        aria-label="Brand Presentation"
        className="hidden md:flex md:w-1/2 bg-[#0a0a0c] border-l border-zinc-800 relative flex-col justify-between p-12 lg:p-20 overflow-hidden"
      >
        <div className="absolute inset-0 z-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 70% 30%, #fcd34d 0%, transparent 50%)' }}></div>
        <div className="relative z-10">
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
        </div>
        <div className="relative z-10 flex flex-col gap-10 mt-16 max-w-lg">
          <div className="space-y-4">
            <div className="inline-flex items-center px-3 py-1 rounded-full border border-amber-500/20 bg-amber-500/10 text-amber-300 text-xs font-medium font-mono mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mr-2 animate-pulse"></span>
              Picks Diarios
            </div>
            <h2 className="font-sans font-bold text-[32px] leading-tight text-white">
              Empieza gratis hoy.
            </h2>
            <p className="font-sans text-[15px] leading-relaxed text-zinc-400">
              Un pick diario. Probabilidades reales. Historial verificable.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
