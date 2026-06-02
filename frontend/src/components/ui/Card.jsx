import React from 'react';

const VARIANTS = {
  default: 'bg-surface border-line',
  elevated: 'bg-surface-elevated border-line-subtle shadow-card',
  interactive:
    'bg-surface border-line hover:border-line-subtle hover:bg-surface-elevated/50 cursor-pointer',
  glass: 'bg-surface/95 backdrop-blur border-line shadow-card',
};

export default function Card({
  children,
  as: Component = 'div',
  variant = 'default',
  className = '',
  ...props
}) {
  return (
    <Component
      className={[
        'rounded-2xl border',
        VARIANTS[variant] || VARIANTS.default,
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </Component>
  );
}
