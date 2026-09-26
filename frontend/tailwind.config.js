export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0c1118",
        panel: "#141b26",
        line: "#2a384c",
        muted: "#93a4b8",
        info: "#3d8bfd",
        ok: "#3d9a6a",
        warn: "#d4a017",
        high: "#e07a2f",
        crit: "#d64545",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
