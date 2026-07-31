/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#EEF2FF",
          100: "#E0E7FF",
          200: "#C7D2FE",
          300: "#A5B4FC",
          400: "#818CF8",
          500: "#4F46E5",
          600: "#4338CA",
          700: "#3730A3",
          800: "#312E81",
          900: "#1E1B4B",
        },
        accent: {
          400: "#06B6D4",
        },
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(90deg, #4F46E5, #06B6D4)",
      },
    },
  },
  plugins: [],
};
