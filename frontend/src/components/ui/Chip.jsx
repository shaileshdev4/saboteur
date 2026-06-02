import React from 'react';

const VARIANTS = {
  default: 'bg-surface-elevated text-ink-200 border-line',
  accent: 'bg-accent text-white border-accent',
  'accent-soft': 'bg-accent-muted text-accent-foreground border-accent/50',
  muted: 'bg-ink-800 text-ink-200 border-ink-600 hover:border-ink-500',
  good: 'bg-good-muted text-good-foreground border-good/50',
  warn: 'bg-warn-muted text-warn-foreground border-warn/50',
  bad: 'bg-bad-muted text-bad-foreground border-bad/50',
};

export default function Chip({
  children,
  variant = 'default',
  active = false,
  className = '',
  as: Component = 'span',
  ...props
}) {
  const activeAccent = active && variant === 'default'
    ? 'bg-accent text-white border-accent font-semibold'
    : VARIANTS[variant] || VARIANTS.default;

  return (
    <Component
      className={[
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium',
        'border whitespace-nowrap transition-colors',
        activeAccent,
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </Component>
  );
}
