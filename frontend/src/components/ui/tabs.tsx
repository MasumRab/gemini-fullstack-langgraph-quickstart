import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'

import { cn } from '@/lib/utils'

/**
 * Renders a tabs root container with default layout styling.
 *
 * @param className - Optional additional CSS class names to merge with the component's defaults
 * @param props - Additional props are forwarded to the underlying root element
 * @returns The rendered tabs root element
 */
function Tabs({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      className={cn('flex flex-col gap-2', className)}
      {...props}
    />
  )
}

/**
 * Render a styled Tabs list wrapper that applies a data-slot and merges default classes with any provided classes.
 *
 * @param className - Additional CSS classes that are merged with the component's default list styles
 * @param props - Additional props forwarded to the underlying Radix `TabsPrimitive.List` component
 * @returns The rendered `TabsPrimitive.List` element with `data-slot="tabs-list"` and combined class names
 */
function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      className={cn(
        'bg-muted text-muted-foreground inline-flex h-9 w-fit items-center justify-center rounded-lg p-[3px]',
        className
      )}
      {...props}
    />
  )
}

/**
 * Render a styled tab trigger element with merged classes and a data-slot attribute.
 *
 * @param className - Additional class names to merge with the component's default styles.
 * @param props - Remaining props forwarded to the underlying Trigger primitive.
 * @returns The tab trigger element configured with data-slot="tabs-trigger" and the combined className.
 */
function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      data-slot="tabs-trigger"
      className={cn(
        "data-[state=active]:bg-background dark:data-[state=active]:text-foreground focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:outline-ring dark:data-[state=active]:border-input dark:data-[state=active]:bg-input/30 text-foreground dark:text-muted-foreground inline-flex h-[calc(100%-1px)] flex-1 items-center justify-center gap-1.5 rounded-md border border-transparent px-2 py-1 text-sm font-medium whitespace-nowrap transition-[color,box-shadow] focus-visible:ring-[3px] focus-visible:outline-1 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:shadow-sm [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

/**
 * Render the tab content element with default layout classes and a data-slot for slot targeting.
 *
 * @param className - Additional CSS class names appended to the default content classes.
 * @param props - Remaining props forwarded to the underlying TabsPrimitive.Content component.
 * @returns The rendered tab content element.
 */
function TabsContent({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot="tabs-content"
      className={cn('flex-1 outline-none', className)}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
