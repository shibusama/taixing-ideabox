/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cream: '#fef9e7',
        pop: {
          red:     '#ff2e3b',
          blue:    '#2d7dff',
          yellow:  '#ffd60a',
          pink:    '#ff4d9d',
          green:   '#00d97e',
          orange:  '#ff8c1a',
          purple:  '#9b4dff',
          cyan:    '#00d4e8',
          black:   '#0a0a0a',
          white:   '#ffffff',
        }
      },
      fontFamily: {
        display: ['Bangers', 'Impact', 'system-ui', 'sans-serif'],
        sans: ['"Space Grotesk"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
      },
      borderWidth: {
        '3': '3px',
        '4': '4px',
        '5': '5px',
      },
      boxShadow: {
        'pop': '4px 4px 0 0 #0a0a0a',
        'pop-sm': '3px 3px 0 0 #0a0a0a',
        'pop-lg': '6px 6px 0 0 #0a0a0a',
        'pop-xl': '8px 8px 0 0 #0a0a0a',
        'pop-pink': '4px 4px 0 0 #ff4d9d',
        'pop-blue': '4px 4px 0 0 #2d7dff',
        'pop-red': '4px 4px 0 0 #ff2e3b',
        'pop-green': '4px 4px 0 0 #00d97e',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.25s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'bounce-in': 'bounceIn 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'wiggle': 'wiggle 0.3s ease-in-out',
        'pop-in': 'popIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.92)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        bounceIn: {
          '0%': { opacity: '0', transform: 'scale(0.8) rotate(-5deg)' },
          '60%': { opacity: '1', transform: 'scale(1.05) rotate(2deg)' },
          '100%': { transform: 'scale(1) rotate(0deg)' },
        },
        wiggle: {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '25%': { transform: 'rotate(-3deg)' },
          '75%': { transform: 'rotate(3deg)' },
        },
        popIn: {
          '0%': { opacity: '0', transform: 'scale(0.8) translateY(10px)' },
          '50%': { transform: 'scale(1.05) translateY(-2px)' },
          '100%': { opacity: '1', transform: 'scale(1) translateY(0)' },
        },
      }
    },
  },
  plugins: [],
}
