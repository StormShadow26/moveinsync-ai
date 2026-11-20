import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: { brand: { blue: '#4285F4', red: '#EA4335', yellow: '#FBBC05', green: '#34A853', ink: '#3C4043' } },
      boxShadow: { material: '0 2px 12px rgba(0,0,0,.08)' },
    },
  },
  plugins: [],
} satisfies Config
