export default function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-label="Health-OS"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Outer hexagon ring */}
      <path
        d="M16 2L28 9V23L16 30L4 23V9L16 2Z"
        stroke="#6366f1"
        strokeWidth="1.5"
        fill="none"
        opacity="0.6"
      />
      {/* Inner cross / health symbol */}
      <rect x="14" y="8" width="4" height="16" rx="1.5" fill="#6366f1" />
      <rect x="8" y="14" width="16" height="4" rx="1.5" fill="#6366f1" />
    </svg>
  )
}
