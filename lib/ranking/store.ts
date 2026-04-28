'use client';

import { useEffect, useState, useCallback } from 'react';

const XP_KEY = 'edgebet.profile.xp';
const AVATAR_PRESET_KEY = 'edgebet.profile.avatar.preset';
const AVATAR_CUSTOM_KEY = 'edgebet.profile.avatar.custom';

export interface ProfileVisuals {
  xp: number;
  avatarPresetId: string | null;
  avatarCustomData: string | null;
}

function readNum(key: string, fallback: number): number {
  if (typeof window === 'undefined') return fallback;
  const raw = window.localStorage.getItem(key);
  const n = raw ? Number(raw) : fallback;
  return Number.isFinite(n) ? n : fallback;
}

function readStr(key: string): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(key);
}

export function useProfileVisuals(): ProfileVisuals & {
  setXp: (xp: number) => void;
  selectPreset: (id: string) => void;
  setCustomAvatar: (dataUrl: string | null) => void;
  clearAvatar: () => void;
} {
  const [xp, setXpState] = useState(0);
  const [avatarPresetId, setAvatarPresetId] = useState<string | null>(null);
  const [avatarCustomData, setAvatarCustomData] = useState<string | null>(null);

  useEffect(() => {
    setXpState(readNum(XP_KEY, 320));
    setAvatarPresetId(readStr(AVATAR_PRESET_KEY) ?? 'edge-1');
    setAvatarCustomData(readStr(AVATAR_CUSTOM_KEY));
  }, []);

  const setXp = useCallback((next: number) => {
    setXpState(next);
    window.localStorage.setItem(XP_KEY, String(next));
  }, []);

  const selectPreset = useCallback((id: string) => {
    setAvatarPresetId(id);
    setAvatarCustomData(null);
    window.localStorage.setItem(AVATAR_PRESET_KEY, id);
    window.localStorage.removeItem(AVATAR_CUSTOM_KEY);
  }, []);

  const setCustomAvatar = useCallback((dataUrl: string | null) => {
    setAvatarCustomData(dataUrl);
    if (dataUrl) {
      window.localStorage.setItem(AVATAR_CUSTOM_KEY, dataUrl);
    } else {
      window.localStorage.removeItem(AVATAR_CUSTOM_KEY);
    }
  }, []);

  const clearAvatar = useCallback(() => {
    setAvatarPresetId('edge-1');
    setAvatarCustomData(null);
    window.localStorage.setItem(AVATAR_PRESET_KEY, 'edge-1');
    window.localStorage.removeItem(AVATAR_CUSTOM_KEY);
  }, []);

  return { xp, avatarPresetId, avatarCustomData, setXp, selectPreset, setCustomAvatar, clearAvatar };
}
