import type { LucideIcon } from "lucide-react";
import { BookOpen, Bot, Gauge, MessageSquare } from "lucide-react";

export type SiteNavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const SITE_NAV_ITEMS: SiteNavItem[] = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/docs", label: "Docs", icon: BookOpen },
];