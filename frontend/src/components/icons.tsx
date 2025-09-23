import type { SVGProps } from 'react'

interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number
}

const baseIconProps = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  role: 'img' as const,
}

export function DownloadIcon({ size = 20, ...rest }: IconProps): JSX.Element {
  return (
    <svg
      {...baseIconProps}
      {...rest}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M12 3v11" />
      <polyline points="7 11 12 16 17 11" />
      <path d="M5 19h14" />
    </svg>
  )
}

export function PlusIcon({ size = 20, ...rest }: IconProps): JSX.Element {
  return (
    <svg
      {...baseIconProps}
      {...rest}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </svg>
  )
}

export function SaveIcon({ size = 20, ...rest }: IconProps): JSX.Element {
  return (
    <svg
      {...baseIconProps}
      {...rest}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M6 4h11l3 3v13H6z" />
      <path d="M6 4h11v6H6z" />
      <rect x="9" y="14" width="6" height="6" rx="1" ry="1" />
    </svg>
  )
}

export function UploadIcon({ size = 20, ...rest }: IconProps): JSX.Element {
  return (
    <svg
      {...baseIconProps}
      {...rest}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M12 21V10" />
      <polyline points="7 13 12 8 17 13" />
      <path d="M5 5h14" />
    </svg>
  )
}
