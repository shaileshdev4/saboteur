import React from 'react';

export default function Textarea({
  className = '',
  ...props
}) {
  return (
    <textarea
      className={[
        'w-full rounded-xl border border-line bg-surface px-3 py-2',
        'font-mono text-sm text-ink-100 placeholder:text-ink-500',
        'transition-colors hover:border-line-subtle',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
        'focus-visible:outline-accent focus-visible:border-accent/60',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className,
      ].join(' ')}
      {...props}
    />
  );
}
