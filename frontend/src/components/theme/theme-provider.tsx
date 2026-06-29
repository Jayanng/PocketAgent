"use client";

import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useState,
} from "react";

export type AppTheme = "light" | "dark";

const STORAGE_KEY = "pocketagent-theme";
const LEGACY_STORAGE_KEY = "pocketagent-landing-theme";

type ThemeContextValue = {
  theme: AppTheme;
  setTheme: (theme: AppTheme) => void;
  toggleTheme: () => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStoredTheme(): AppTheme | null {
  if (typeof window === "undefined") return null;
  const stored =
    localStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(LEGACY_STORAGE_KEY);
  return stored === "dark" || stored === "light" ? stored : null;
}

function persistTheme(theme: AppTheme) {
  localStorage.setItem(STORAGE_KEY, theme);
  localStorage.setItem(LEGACY_STORAGE_KEY, theme);
}

export function applyThemeToDocument(theme: AppTheme) {
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);
  root.setAttribute("data-landing-theme", theme);
  root.classList.remove("theme-light", "theme-dark");
  root.classList.add(theme === "light" ? "theme-light" : "theme-dark");
}

function getInitialTheme(): AppTheme {
  return readStoredTheme() ?? "light";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<AppTheme>(getInitialTheme);

  useLayoutEffect(() => {
    applyThemeToDocument(theme);
  }, [theme]);

  const setTheme = useCallback((next: AppTheme) => {
    persistTheme(next);
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => {
      const next: AppTheme = prev === "light" ? "dark" : "light";
      persistTheme(next);
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}