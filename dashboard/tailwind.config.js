/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0f1117',
          card: '#1a1d27',
          elevated: '#20243a',
          border: '#2a2d3e',
        },
        accent: {
          DEFAULT: '#6366f1',
          hover: '#4f52d4',
          muted: 'rgba(99,102,241,0.15)',
        },
        text: {
          primary: '#e8eaf6',
          secondary: '#8b8fa8',
          muted: '#565975',
        },
        status: {
          normal: '#22c55e',
          low: '#f59e0b',
          high: '#f59e0b',
          critical: '#ef4444',
          critical_low: '#ef4444',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'card-shine': 'linear-gradient(135deg, rgba(99,102,241,0.05) 0%, transparent 60%)',
      },
    },
  },
  plugins: [],
}
