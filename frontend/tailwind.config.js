/** @type {import('tailwindcss').Config} */
// -------------------------------------------------------------------------
// THEME: medical-green placeholder palette for 1Health Pharmacy.
// These are the ONLY place brand colors are defined — swap the hex values for
// the site's exact tokens (grab them via DevTools on 1healthpharmacy.in) and
// the whole widget re-themes. `brand-500` is the primary action color.
// -------------------------------------------------------------------------
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Placeholder values supplied by the client (2026-07-16); swap for the
        // exact DevTools tokens from 1healthpharmacy.in when available.
        brand: {
          50: "#E8F5EE", // light green
          100: "#C7E9D5",
          200: "#9BD9B5",
          300: "#5FC489",
          400: "#20B368",
          500: "#00A651", // primary green
          600: "#008A45",
          700: "#007A3D", // dark green
          800: "#00632F",
          900: "#004D25",
        },
        ink: "#1A1A1A", // dark text
        muted: "#6B7280", // gray text
      },
      fontFamily: {
        sans: [
          "Inter",
          "Poppins",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      boxShadow: {
        chat: "0 12px 40px rgba(9, 107, 60, 0.18)",
        bubble: "0 8px 24px rgba(9, 107, 60, 0.35)",
      },
      keyframes: {
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(16px) scale(0.98)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        blink: {
          "0%, 80%, 100%": { opacity: "0.2" },
          "40%": { opacity: "1" },
        },
      },
      animation: {
        "slide-up": "slide-up 0.22s ease-out",
        blink: "blink 1.2s infinite both",
      },
    },
  },
  plugins: [],
};
