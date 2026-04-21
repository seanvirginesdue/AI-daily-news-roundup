import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#d63c2f",
          dark:    "#b83326",
          light:   "#ffecea",
        },
      },
    },
  },
  plugins: [],
};

export default config;
