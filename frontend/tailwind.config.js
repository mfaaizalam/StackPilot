/** @type {import('tailwindcss').Config} */
const v = (name) => `rgb(var(--color-${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: v('canvas'),
        surface: { DEFAULT: v('surface'), 2: v('surface-2') },
        line: v('line'),
        ink: { DEFAULT: v('ink'), muted: v('ink-muted') },
        brand: {
          DEFAULT: v('brand'),
          hover: v('brand-hover'),
          fg: v('brand-fg'),
          soft: v('brand-soft'),
        },
        success: { DEFAULT: v('success'), soft: v('success-soft') },
        warning: { DEFAULT: v('warning'), soft: v('warning-soft') },
        danger: { DEFAULT: v('danger'), soft: v('danger-soft') },
        info: v('info'),
      },
      fontFamily: { sans: ['var(--font-sans)'] },
      borderRadius: { card: 'var(--radius-card)' },
    },
  },
  plugins: [],
};