import * as React from 'react'
import * as ScrollAreaPrimitive from '@radix-ui/react-scroll-area'

import { cn } from '@/lib/utils'

/**
 * Wrapper around Radix ScrollArea Root that provides a standardized viewport, scrollbar, and corner.
 *
 * @param className - Optional additional CSS classes applied to the root container
 * @param children - Content rendered inside the scroll viewport
 * @param props - Additional props forwarded to `ScrollAreaPrimitive.Root`
 * @returns The composed scroll area root element
 */
function ScrollArea({
  className,
  children,
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.Root>) {
  return (
    <ScrollAreaPrimitive.Root
      data-slot="scroll-area"
      className={cn('relative', className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        data-slot="scroll-area-viewport"
        className="focus-visible:ring-ring/50 size-full rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:ring-[3px] focus-visible:outline-1"
        style={{ overscrollBehavior: 'none' }}
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollBar />
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
}

/**
 * Renders a styled scrollbar for a ScrollArea with configurable orientation.
 *
 * @param className - Additional CSS classes to apply to the scrollbar container
 * @param orientation - Scrollbar orientation, either `'vertical'` or `'horizontal'` (defaults to `'vertical'`)
 * @returns A React element representing the styled ScrollArea scrollbar
 */
function ScrollBar({
  className,
  orientation = 'vertical',
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>) {
  return (
    <ScrollAreaPrimitive.ScrollAreaScrollbar
      data-slot="scroll-area-scrollbar"
      orientation={orientation}
      className={cn(
        'flex touch-none p-px transition-colors select-none',
        orientation === 'vertical' && 'h-full w-1.5 border-l border-l-transparent',
        orientation === 'horizontal' && 'h-1.5 flex-col border-t border-t-transparent',
        className
      )}
      {...props}
    >
      <ScrollAreaPrimitive.ScrollAreaThumb
        data-slot="scroll-area-thumb"
        className="bg-neutral-600/30 relative flex-1 rounded-full"
      />
    </ScrollAreaPrimitive.ScrollAreaScrollbar>
  )
}

export { ScrollArea, ScrollBar }
