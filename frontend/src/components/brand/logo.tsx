import Image from "next/image";
import Link from "next/link";

import { cn } from "@/lib/utils";

const SIZE_MAP = {
  xs: 24,
  sm: 28,
  md: 32,
  lg: 40,
} as const;

type LogoProps = {
  size?: keyof typeof SIZE_MAP;
  showText?: boolean;
  href?: string | null;
  className?: string;
  textClassName?: string;
  accentClassName?: string;
  onClick?: () => void;
};

export function Logo({
  size = "md",
  showText = true,
  href = "/",
  className,
  textClassName,
  accentClassName,
  onClick,
}: LogoProps) {
  const dimension = SIZE_MAP[size];

  const content = (
    <span className={cn("inline-flex min-w-0 items-center gap-2 sm:gap-2.5", className)}>
      <Image
        src="/logo.png"
        alt="PocketAgent"
        width={dimension}
        height={dimension}
        className="shrink-0 rounded-full object-cover"
        priority={size === "md" || size === "lg"}
      />
      {showText && (
        <span className={cn("truncate font-semibold tracking-tight", textClassName)}>
          Pocket<span className={accentClassName}>Agent</span>
        </span>
      )}
    </span>
  );

  if (href) {
    return (
      <Link href={href} className="group min-w-0" onClick={onClick}>
        {content}
      </Link>
    );
  }

  return content;
}