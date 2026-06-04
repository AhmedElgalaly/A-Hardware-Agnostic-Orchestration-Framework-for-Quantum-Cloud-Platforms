/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        panel: "#f7f8fb",
        line: "#d9dee8",
        quantum: "#216869"
      }
    }
  },
  plugins: []
};
