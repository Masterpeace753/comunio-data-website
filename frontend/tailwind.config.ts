import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: { extend: { colors: { canvas: "var(--bg-canvas)", surface: "var(--bg-surface)", elevated: "var(--bg-surface-elevated)", line: "var(--border-subtle)", ink: "var(--text-primary)", secondary: "var(--text-secondary)", muted: "var(--text-muted)", accent: "var(--accent-blue)", violet: "var(--accent-violet)", success: "var(--success)", danger: "var(--danger)" }, fontFamily: { sans: ["var(--font-geist-sans)"], mono: ["var(--font-geist-mono)"] } } },
  plugins: []
};
export default config;