import React from 'react';
import Button from './ui/Button.jsx';

export default function DomainPicker({ domains, selected, onChange, disabled }) {
  if (!domains || domains.length === 0) return null;
  return (
    <div
      className="inline-flex bg-surface border border-line rounded-xl p-1 overflow-x-auto max-w-full gap-0.5"
      role="group"
      aria-label="Domain"
    >
      {domains.map((d) => (
        <Button
          key={d.id}
          type="button"
          variant={selected === d.id ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => onChange(d.id)}
          disabled={disabled}
          aria-pressed={selected === d.id}
          title={d.description}
          className="whitespace-nowrap"
        >
          {d.label}
        </Button>
      ))}
    </div>
  );
}
