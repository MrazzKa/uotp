import tailwindcssAnimate from "tailwindcss-animate";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "var(--border)",
        background: "var(--bg)",
        foreground: "var(--text)",
        surface: "var(--surface)",
        surface2: "var(--surface-2)",
        muted: "var(--surface-2)",
        mutedText: "var(--text-muted)",
        primary: "var(--primary)",
        primaryHover: "var(--primary-hover)",
        primarySoft: "var(--primary-soft)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        info: "var(--info)"
      },
      borderRadius: {
        panel: "16px",
        control: "12px",
        chip: "9999px"
      },
      boxShadow: {
        base: "var(--shadow-base)",
        card: "var(--shadow-card)",
        raised: "var(--shadow-raised)"
      },
      fontFamily: {
        sans: ["InterVariable", "Inter", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: [tailwindcssAnimate]
};
