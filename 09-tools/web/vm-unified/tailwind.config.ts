import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        vm: {
          bg: '#0F0F0F',
          surface: '#1A1A1A',
          'surface-elevated': '#242424',
          border: '#2A2A2A',
          ink: '#F5F5F5',
          'ink-muted': '#8A8A8A',
          'ink-subtle': '#5A5A5A',
          primary: '#FF6B35',
          'primary-dim': 'rgba(255, 107, 53, 0.12)',
          success: '#4ADE80',
          warning: '#FBBF24',
          error: '#F87171',
          hover: 'rgba(255, 255, 255, 0.06)',
          active: 'rgba(255, 255, 255, 0.1)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'vm-sm': '6px',
        'vm-md': '10px',
        'vm-lg': '14px',
        'vm-xl': '20px',
      },
      boxShadow: {
        'vm-sm': '0 1px 2px rgba(0, 0, 0, 0.3)',
        'vm-md': '0 4px 12px rgba(0, 0, 0, 0.4)',
        'vm-lg': '0 8px 24px rgba(0, 0, 0, 0.5)',
        'vm-glow': '0 0 20px rgba(255, 107, 53, 0.15)',
      },
    },
  },
  plugins: [],
}

export default config
