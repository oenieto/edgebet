'use client';

import { useRef, useState } from 'react';
import { Camera, Check, Trash2, Upload } from 'lucide-react';

import Avatar, { PresetSvg } from './Avatar';
import { PRESET_AVATARS, avatarById } from '@/lib/ranking/avatars';

interface Props {
  presetId: string | null;
  customDataUrl: string | null;
  initials: string;
  ringColor?: string;
  onSelectPreset: (id: string) => void;
  onUploadCustom: (dataUrl: string) => void;
  onClear: () => void;
}

const MAX_BYTES = 1.5 * 1024 * 1024;

export default function AvatarPicker({
  presetId,
  customDataUrl,
  initials,
  ringColor,
  onSelectPreset,
  onUploadCustom,
  onClear,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFile = (file: File) => {
    setUploadError(null);
    if (!file.type.startsWith('image/')) {
      setUploadError('Solo imágenes (PNG, JPG, WebP).');
      return;
    }
    if (file.size > MAX_BYTES) {
      setUploadError('Máximo 1.5 MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result === 'string') onUploadCustom(result);
    };
    reader.onerror = () => setUploadError('No se pudo leer la imagen.');
    reader.readAsDataURL(file);
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-5">
        <Avatar
          presetId={presetId}
          customDataUrl={customDataUrl}
          initials={initials}
          size={88}
          ringColor={ringColor}
        />
        <div className="flex flex-col gap-2">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-2 h-[36px] px-4 rounded-full bg-white text-[#0a0a0c] font-sans text-[12px] font-bold hover:bg-zinc-200 transition-colors"
          >
            <Upload className="w-3.5 h-3.5" />
            Subir foto
          </button>
          {(customDataUrl || presetId !== 'edge-1') && (
            <button
              type="button"
              onClick={onClear}
              className="inline-flex items-center gap-2 h-[36px] px-4 rounded-full bg-white/5 border border-white/[0.08] text-zinc-300 font-sans text-[12px] font-semibold hover:bg-white/10 hover:text-white transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Quitar
            </button>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
              e.target.value = '';
            }}
          />
        </div>
      </div>

      {uploadError && (
        <p className="font-sans text-[12px] text-red-400">{uploadError}</p>
      )}

      <div>
        <div className="flex items-center gap-2 mb-3">
          <Camera className="w-3.5 h-3.5 text-zinc-500" />
          <span className="font-sans text-[11px] uppercase tracking-widest text-zinc-500 font-semibold">
            Galería
          </span>
        </div>
        <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
          {PRESET_AVATARS.map((p) => {
            const selected = !customDataUrl && presetId === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => onSelectPreset(p.id)}
                className={`relative rounded-full overflow-hidden transition-transform hover:scale-105 ${
                  selected ? 'ring-2 ring-white' : 'ring-1 ring-white/10'
                }`}
                aria-label={`Avatar ${p.label}`}
                title={p.label}
              >
                {avatarById(p.id).imageUrl ? (
                  <img src={avatarById(p.id).imageUrl} alt={p.label} width={56} height={56} className="w-full h-full object-cover" />
                ) : (
                  <PresetSvg preset={avatarById(p.id)} size={56} initials={initials} />
                )}
                {selected && (
                  <span className="absolute inset-0 flex items-center justify-center bg-black/40">
                    <Check className="w-4 h-4 text-white" />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
