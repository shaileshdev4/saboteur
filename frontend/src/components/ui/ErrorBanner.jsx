import React from 'react';
import { AlertCircle } from 'lucide-react';
import Button from './Button.jsx';

export default function ErrorBanner({
  message,
  onDismiss,
  onRetry,
  retryLabel = 'Retry',
  retrying = false,
}) {
  if (!message) return null;

  return (
    <div
      role="alert"
      className="panel-bad border-y border-bad/50 px-4 py-3 text-sm text-bad-foreground flex flex-wrap items-start gap-3"
    >
      <AlertCircle size={18} className="shrink-0 mt-0.5" aria-hidden />
      <p className="flex-1 min-w-[12rem] leading-relaxed">{message}</p>
      <div className="flex items-center gap-2 shrink-0">
        {onRetry && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onRetry}
            disabled={retrying}
          >
            {retryLabel}
          </Button>
        )}
        {onDismiss && (
          <Button variant="ghost" size="sm" onClick={onDismiss} className="!px-2">
            Dismiss
          </Button>
        )}
      </div>
    </div>
  );
}
