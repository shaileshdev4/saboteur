/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Sora', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        ink: {
          50: '#f7f7f8',
          100: '#eeeef1',
          200: '#d8d9de',
          300: '#b3b5bd',
          400: '#888a96',
          500: '#666873',
          600: '#494b54',
          700: '#33353c',
          800: '#1f2126',
          900: '#0f1014',
        },
        surface: {
          DEFAULT: 'var(--color-surface)',
          elevated: 'var(--color-surface-elevated)',
        },
        /* Named "line" — not "border" (avoids clashing with border-width utility) */
        line: {
          DEFAULT: 'var(--color-line)',
          subtle: 'var(--color-line-subtle)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          soft: 'var(--color-accent-soft)',
        },
        /* Flat keys — avoids bg-warn-muted being parsed as bg-warn + opacity "muted" */
        'accent-muted': 'var(--color-accent-muted)',
        'accent-foreground': 'var(--color-accent-fg)',
        good: {
          DEFAULT: 'var(--color-good)',
        },
        'good-muted': 'var(--color-good-muted)',
        'good-foreground': 'var(--color-good-fg)',
        warn: {
          DEFAULT: 'var(--color-warn)',
        },
        'warn-muted': 'var(--color-warn-muted)',
        'warn-foreground': 'var(--color-warn-fg)',
        bad: {
          DEFAULT: 'var(--color-bad)',
        },
        'bad-muted': 'var(--color-bad-muted)',
        'bad-foreground': 'var(--color-bad-fg)',
      },
      borderRadius: {
        md: '12px',
        lg: '16px',
        xl: '16px',
        '2xl': '16px',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        glow: 'var(--shadow-glow)',
      },
      spacing: {
        1: 'var(--space-1)',
        2: 'var(--space-2)',
        3: 'var(--space-3)',
        4: 'var(--space-4)',
        5: 'var(--space-5)',
        6: 'var(--space-6)',
      },
    },
  },
  plugins: [],
};
