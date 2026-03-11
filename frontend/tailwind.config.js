/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        app: '#f8fafc', // slate-50
        page: '#ffffff', // white
        card: '#ffffff', // white
        elevated: '#ffffff', // white
        border: {
          subtle: '#f1f5f9', // slate-100
          DEFAULT: '#e2e8f0', // slate-200
        },
        content: {
          primary: '#0f172a', // slate-900
          secondary: '#64748b', // slate-500
          tertiary: '#94a3b8', // slate-400
        },
        positive: {
          DEFAULT: '#10b981', // emerald-500
          bg: '#ecfdf5', // emerald-50
          border: '#d1fae5', // emerald-100
        },
        negative: {
          DEFAULT: '#ef4444', // red-500
          bg: '#fef2f2', // red-50
          border: '#fee2e2', // red-100
        },
        warning: {
          DEFAULT: '#f59e0b', // amber-500
          bg: '#fffbeb', // amber-50
          border: '#fef3c7', // amber-100
        },
        info: {
          DEFAULT: '#3b82f6', // blue-500
          bg: '#eff6ff', // blue-50
          border: '#dbeafe', // blue-100
        },
        surface: {
          hover: '#f1f5f9', // slate-100
          selected: '#e2e8f0', // slate-200
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        sm: '0 1px 2px 0 rgba(0, 0, 0, 0.02)',
        DEFAULT: '0 1px 3px 0 rgba(0, 0, 0, 0.03), 0 1px 2px -1px rgba(0, 0, 0, 0.02)',
        md: '0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -2px rgba(0, 0, 0, 0.02)',
        lg: '0 10px 15px -3px rgba(0, 0, 0, 0.03), 0 4px 6px -4px rgba(0, 0, 0, 0.02)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in': 'slideIn 0.3s ease-out',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
