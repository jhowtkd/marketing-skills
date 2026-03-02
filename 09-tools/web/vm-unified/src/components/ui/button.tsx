import * as React from 'react'
import { cn } from '@/lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    const variants = {
      primary: 'bg-vm-primary text-white hover:opacity-90',
      secondary: 'bg-vm-surface-elevated text-vm-ink hover:bg-vm-hover',
      ghost: 'text-vm-ink-muted hover:text-vm-ink hover:bg-vm-hover',
      danger: 'bg-vm-error/10 text-vm-error hover:bg-vm-error/20',
    }

    const sizes = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm',
      lg: 'h-12 px-6 text-base',
    }

    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center rounded-vm-md font-medium transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-vm-primary/20',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variants[variant],
          sizes[size],
          className
        )}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button }
