import * as React from 'react'
import { cn } from '@/lib/utils'

export interface KbdProps extends React.HTMLAttributes<HTMLElement> {}

const Kbd = React.forwardRef<HTMLElement, KbdProps>(
  ({ className, ...props }, ref) => {
    return (
      <kbd
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center',
          'h-5 min-w-[20px] px-1 rounded text-[10px] font-mono font-medium',
          'bg-vm-surface-elevated text-vm-ink-muted border border-vm-border',
          className
        )}
        {...props}
      />
    )
  }
)
Kbd.displayName = 'Kbd'

export { Kbd }
