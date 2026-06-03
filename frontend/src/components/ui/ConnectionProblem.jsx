import React from 'react';
import { WifiOff } from 'lucide-react';
import Button from './Button.jsx';
import Card from './Card.jsx';

export default function ConnectionProblem({ message, onRetry, retrying = false }) {
  return (
    <div className="layout-shell py-16 flex justify-center">
      <Card className="max-w-md w-full p-6 text-center space-y-4">
        <WifiOff size={32} className="mx-auto text-ink-500" aria-hidden />
        <h2 className="text-lg font-semibold text-ink-100">API unavailable</h2>
        <p className="text-sm text-ink-400 leading-relaxed">
          {message || "We couldn't connect to the game server. Other tabs may not work until it's back."}
        </p>
        {onRetry && (
          <Button variant="primary" onClick={onRetry} disabled={retrying}>
            {retrying ? 'Connecting…' : 'Try again'}
          </Button>
        )}
      </Card>
    </div>
  );
}
