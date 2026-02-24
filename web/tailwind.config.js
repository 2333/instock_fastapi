/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // TradingView/Binance inspired dark theme
        'bg-primary': '#0d0d0d',
        'bg-secondary': '#1a1a1a',
        'bg-tertiary': '#242424',
        'bg-hover': '#2a2a2a',
        
        // Accent colors
        'accent-blue': '#2962ff',
        'accent-green': '#00c853',
        'accent-red': '#ff1744',
        'accent-orange': '#ff9100',
        'accent-purple': '#6200ea',
        
        // Text colors
        'text-primary': '#ffffff',
        'text-secondary': '#b0b0b0',
        'text-muted': '#6b7280',
        
        // Border
        'border-light': '#2a2a2a',
        'border-dark': '#1f1f1f',
      },
      fontFamily: {
        'mono': ['JetBrains Mono', 'SF Mono', 'Monaco', 'Consolas', 'monospace'],
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      boxShadow: {
        'glow-green': '0 0 20px rgba(0, 200, 83, 0.3)',
        'glow-red': '0 0 20px rgba(255, 23, 68, 0.3)',
        'glow-blue': '0 0 20px rgba(41, 98, 255, 0.3)',
      },
    },
  },
  plugins: [],
}
