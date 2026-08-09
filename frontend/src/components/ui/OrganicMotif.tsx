interface OrganicMotifProps {
  className?: string;
  variant?: "bloom" | "orbit" | "sprout";
}

export function OrganicMotif({
  className = "",
  variant = "sprout",
}: OrganicMotifProps) {
  return (
    <svg
      aria-hidden="true"
      className={`organic-motif organic-motif--${variant} ${className}`.trim()}
      fill="none"
      viewBox="0 0 240 240"
    >
      {variant === "sprout" && (
        <>
          <path d="M121 207c-2-61 4-109 38-150" />
          <path d="M130 147c25-3 47-19 56-43-27-2-49 13-56 43Z" />
          <path d="M119 174c-25-4-44-20-51-44 26 0 47 16 51 44Z" />
          <circle cx="159" cy="57" r="8" />
        </>
      )}
      {variant === "bloom" && (
        <>
          <path d="M120 119c-45-17-51-55-31-73 23 6 37 27 31 73Z" />
          <path d="M121 119c17-45 55-51 73-31-6 23-27 37-73 31Z" />
          <path d="M120 121c45 17 51 55 31 73-23-6-37-27-31-73Z" />
          <path d="M119 120c-17 45-55 51-73 31 6-23 27-37 73-31Z" />
          <circle cx="120" cy="120" r="18" />
        </>
      )}
      {variant === "orbit" && (
        <>
          <circle cx="120" cy="120" r="72" />
          <path d="M48 122c25 22 55 32 89 28 26-3 48-15 65-34" />
          <circle cx="180" cy="80" r="11" />
          <circle cx="76" cy="168" r="6" />
        </>
      )}
    </svg>
  );
}
