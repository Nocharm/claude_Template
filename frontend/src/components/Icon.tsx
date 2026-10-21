// Inline stroke icons (no icon font/emoji) so they inherit text color.

const PATHS = {
  home: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
  book: "M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 21V5",
  map: "M8.4 6.3l7.2 1.3M7.2 8.2l3.6 7.6M16.8 10.2l-3.6 5.6M8.5 6a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0zM20.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0zM14.5 18a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z",
  back: "M15 5l-7 7 7 7",
  forward: "M9 5l7 7-7 7",
  play: "M8 5l11 7-11 7z",
  check:
    "M7 4h10a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3zM8.5 12l2.5 2.5 4.5-5",
} as const;

interface IconProps {
  name: keyof typeof PATHS;
  size?: number;
}

export function Icon({ name, size = 24 }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
