/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark-gray': '#1a1a1a',
        'darker-gray': '#141414',
        'user-gray': '#2a2a2a',
        'light-gray': '#e2e8f0',
        blue: {
          600: '#2563eb',
          700: '#1d4ed8',
        },
      },
      spacing: {
        '1%': '1%',
        '2%': '2%',
        '3%': '3%',
        '4%': '4%',
        '10%': '10%',
        '20.5%': '20.5%',
        // Add more percentage values as needed
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('tailwind-scrollbar'),
  ],
}