'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';

import AppHeader from '@/components/shell/AppHeader';
import { useAuth } from '@/contexts/AuthContext';
import { useUserStore } from '@/lib/store/userStore';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated, isHydrated } = useAuth();
  const storeUser = useUserStore((state) => state.user);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isHydrated && !isAuthenticated) {
      router.replace(`/login?from=${encodeURIComponent(pathname)}`);
    } else if (isHydrated && isAuthenticated && storeUser && !storeUser.onboarding_done) {
      router.replace('/onboarding');
    }
  }, [isHydrated, isAuthenticated, storeUser, router, pathname]);

  if (!isHydrated || !isAuthenticated || (storeUser && !storeUser.onboarding_done)) {
    return (
      <div className="min-h-screen bg-[#0a0a0c] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
          <p className="font-sans text-[13px] text-zinc-500">Verificando sesión…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-zinc-100">
      <AppHeader />
      <main>{children}</main>
    </div>
  );
}
