/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'Avenir Next', 'Segoe UI', 'sans-serif'],
        display: ['Outfit', 'Avenir Next', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        ink: {
          50: '#eef4ff',
          100: '#d9e7ff',
          900: '#091326',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(61, 111, 255, 0.15), 0 12px 24px rgba(25, 51, 119, 0.18)',
      },
      backgroundImage: {
        'mesh-light': 'radial-gradient(1200px 700px at 15% 0%, rgba(61,111,255,0.18), transparent 60%), radial-gradient(1000px 700px at 100% 10%, rgba(19,199,180,0.14), transparent 55%), linear-gradient(180deg, #f5f8ff 0%, #ecf4ff 100%)',
        'mesh-dark': 'radial-gradient(1200px 700px at 15% 0%, rgba(83,130,255,0.2), transparent 60%), radial-gradient(1000px 700px at 100% 10%, rgba(28,189,176,0.16), transparent 55%), linear-gradient(180deg, #0a1222 0%, #0d1529 100%)',
      },
    },
  },
  plugins: [],
}
