/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "fade-up": { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "none" } },
        "scale-in": { from: { opacity: "0", transform: "scale(.97) translateY(8px)" }, to: { opacity: "1", transform: "none" } },
        "toast-in": { from: { opacity: "0", transform: "translateY(12px) scale(.98)" }, to: { opacity: "1", transform: "none" } },
        shake: {
          "0%,100%": { transform: "translateX(0)" },
          "20%,60%": { transform: "translateX(-5px)" },
          "40%,80%": { transform: "translateX(5px)" },
        },
        progreso: { "0%": { transform: "translateX(-100%)" }, "100%": { transform: "translateX(250%)" } },
        shimmer: { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
        pop: { "0%": { transform: "scale(1)" }, "50%": { transform: "scale(1.12)" }, "100%": { transform: "scale(1)" } },
      },
      animation: {
        "fade-in": "fade-in .2s ease-out both",
        "fade-up": "fade-up .28s cubic-bezier(.2,.8,.2,1) both",
        "scale-in": "scale-in .22s cubic-bezier(.2,.8,.2,1) both",
        "toast-in": "toast-in .25s cubic-bezier(.2,.8,.2,1) both",
        shake: "shake .35s ease-in-out",
        progreso: "progreso 1.1s ease-in-out infinite",
        shimmer: "shimmer 1.4s linear infinite",
        pop: "pop .25s ease-out",
      },
    },
  },
  plugins: [],
};
