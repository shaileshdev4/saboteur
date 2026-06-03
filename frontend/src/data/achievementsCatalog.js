/**
 * Full achievement list (mirrors backend/achievements.py).
 * `hint` — short line shown on hover when locked.
 */
export const ACHIEVEMENTS_CATALOG = [
  {
    id: 'first_catch',
    name: 'First Catch',
    description: 'Caught your first sabotaged step.',
    hint: 'Flag a round where the AI hid an error.',
    icon: 'target',
    tier: 'bronze',
  },
  {
    id: 'ten_rounds',
    name: 'Warmed Up',
    description: 'Played 10 rounds.',
    hint: 'Complete 10 audit rounds.',
    icon: 'activity',
    tier: 'bronze',
  },
  {
    id: 'fifty_rounds',
    name: 'Persistent',
    description: 'Played 50 rounds.',
    hint: 'Complete 50 rounds.',
    icon: 'zap',
    tier: 'silver',
  },
  {
    id: 'no_over_trust_streak_10',
    name: 'Vigilant',
    description: '10 rounds without a single over-trust.',
    hint: 'Play 10 rounds — never trust a bad solution.',
    icon: 'shield',
    tier: 'silver',
  },
  {
    id: 'score_80',
    name: 'Well-Calibrated',
    description: 'Reached calibration score 80.',
    hint: 'Raise your calibration score to 80.',
    icon: 'chart',
    tier: 'silver',
  },
  {
    id: 'score_95',
    name: 'Sharp',
    description: 'Reached calibration score 95.',
    hint: 'Reach calibration score 95.',
    icon: 'award',
    tier: 'gold',
  },
  {
    id: 'four_domains',
    name: 'Polymath',
    description: 'Played rounds in all four domains.',
    hint: 'Play at least one round in each domain.',
    icon: 'brain',
    tier: 'silver',
  },
  {
    id: 'rating_1300',
    name: 'Rated 1300',
    description: 'Elo rating crossed 1300.',
    hint: 'Grow your Elo rating past 1300.',
    icon: 'star',
    tier: 'gold',
  },
  {
    id: 'all_domains_score_70',
    name: 'Four-Way Calibrated',
    description: 'Hit score 70+ in every domain (3+ rounds each).',
    hint: 'Score 70+ in all four domains (3+ rounds each).',
    icon: 'trophy',
    tier: 'gold',
  },
  {
    id: 'catch_all_misconceptions_once',
    name: 'Encyclopedist',
    description: 'Caught at least one of 20+ algebra misconceptions.',
    hint: 'Catch 20+ distinct misconception types.',
    icon: 'book',
    tier: 'gold',
  },
];

export const ACHIEVEMENT_BY_ID = Object.fromEntries(
  ACHIEVEMENTS_CATALOG.map((a) => [a.id, a]),
);
