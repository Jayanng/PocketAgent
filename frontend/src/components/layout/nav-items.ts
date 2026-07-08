import type { LucideIcon } from "lucide-react";
import { BookOpen, Bot, CalendarClock, Gauge, MessageSquare } from "lucide-react";

export type SiteNavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const SITE_NAV_ITEMS: SiteNavItem[] = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/scheduled-tasks", label: "Automations", icon: CalendarClock },
  { href: "/docs", label: "Docs", icon: BookOpen },
];