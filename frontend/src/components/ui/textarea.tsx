import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Styled textarea component that forwards all native textarea props and composes internal styles with an optional `className`.
 *
 * @param className - Additional CSS class names to merge with the component's predefined styling.
 * @param props - All other standard textarea props are forwarded to the underlying `<textarea>` element.
 * @returns The rendered `<textarea>` element with composed classes and forwarded props.
 */
function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive dark:bg-input/30 flex field-sizing-content min-h-16 w-full rounded-md border bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
