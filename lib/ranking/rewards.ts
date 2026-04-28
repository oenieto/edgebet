import type { RankId } from './tiers';

export type RewardKind = 'free_pick' | 'discount' | 'priority' | 'event' | 'beta';

export interface Reward {
  id: string;
  rankRequired: RankId;
  kind: RewardKind;
  title: string;
  description: string;
}

export const REWARDS: Reward[] = [
  {
    id: 'monthly_free_pick_1',
    rankRequired: 'estratega',
    kind: 'free_pick',
    title: '1 pick Premium gratis al mes',
    description: 'Recibe un pick con edge ≥ 5% sin necesidad de plan Pro.',
  },
  {
    id: 'monthly_free_pick_3',
    rankRequired: 'cazador',
    kind: 'free_pick',
    title: '3 picks Premium gratis al mes',
    description: 'Más picks con valor + acceso anticipado a ligas nuevas.',
  },
  {
    id: 'priority_support',
    rankRequired: 'cazador',
    kind: 'priority',
    title: 'Soporte prioritario',
    description: 'Respuesta en menos de 4 horas hábiles.',
  },
  {
    id: 'monthly_free_pick_5',
    rankRequired: 'maestro',
    kind: 'free_pick',
    title: '5 picks Premium gratis al mes',
    description: 'Incluye 1 pick VIP cortesía cada semana.',
  },
  {
    id: 'beta_features',
    rankRequired: 'maestro',
    kind: 'beta',
    title: 'Acceso beta a nuevos modelos',
    description: 'Probás features experimentales antes que nadie.',
  },
  {
    id: 'upgrade_discount',
    rankRequired: 'leyenda',
    kind: 'discount',
    title: '50% off en upgrade VIP',
    description: 'Mantén el descuento mientras conserves el rango.',
  },
  {
    id: 'mx_event_access',
    rankRequired: 'elite_mx',
    kind: 'event',
    title: 'Eventos exclusivos en México',
    description: 'Meetups, watch parties y networking con apostadores top.',
  },
  {
    id: 'mx_event_invite_plus_one',
    rankRequired: 'elite_mx',
    kind: 'event',
    title: 'Invitación +1 a eventos MX',
    description: 'Llevá a un acompañante a cada evento.',
  },
];

export function rewardsForRank(rank: RankId, allRanks: RankId[]): Reward[] {
  const rankIdx = allRanks.indexOf(rank);
  return REWARDS.filter((r) => allRanks.indexOf(r.rankRequired) <= rankIdx);
}
