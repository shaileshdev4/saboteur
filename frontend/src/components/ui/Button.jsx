import React from 'react';

const VARIANTS = {
  primary:
    'bg-accent text-white hover:bg-accent-soft active:opacity-95 border border-accent',
  secondary:
    'bg-ink-700 text-ink-100 hover:bg-ink-600 border border-line-subtle active:bg-ink-600',
  ghost:
    'bg-transparent text-ink-300 hover:text-ink-100 hover:bg-ink-800 border border-transparent',
  danger:
    'bg-bad-muted text-bad-foreground border border-bad/50 hover:bg-bad/20',
};

const SIZES = {
  sm: 'px-2.5 py-1 text-xs rounded-lg',
  md: 'px-4 py-2 text-sm rounded-xl',
  lg: 'px-5 py-2.5 text-base rounded-xl',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled,
  type = 'button',
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={[
        'inline-flex items-center justify-center font-semibold transition-all',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
        'focus-visible:outline-accent',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none',
        VARIANTS[variant] || VARIANTS.primary,
        SIZES[size] || SIZES.md,
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </button>
  );
}
