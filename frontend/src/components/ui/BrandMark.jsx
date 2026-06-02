import { Scan } from 'lucide-react';

/** Theme A "audit lens" mark */
export default function BrandMark({ size = 'md', className = '' }) {
  const box =
    size === 'lg'
      ? 'w-11 h-11 rounded-xl'
      : 'w-9 h-9 rounded-lg';
  const icon = size === 'lg' ? 22 : 18;

  return (
    <div
      className={[
        box,
        'bg-gradient-to-br from-accent to-cyan-500/80',
        'grid place-items-center flex-shrink-0 shadow-glow audit-lens-ring',
        className,
      ].join(' ')}
      aria-hidden
    >
      <Scan size={icon} className="text-white" strokeWidth={2.25} />
    </div>
  );
}
