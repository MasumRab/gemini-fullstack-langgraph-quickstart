import * as React from 'react'

import { cn } from '@/lib/utils'

/**
 * Base container component for a card layout that applies default card styling and forwards remaining div props.
 *
 * @param className - Additional CSS class names to merge with the card's default classes
 * @returns A div element serving as the card container with composed class names and forwarded props
 */
function Card({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card"
      className={cn(
        'bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm',
        className
      )}
      {...props}
    />
  )
}

/**
 * Header section for a Card component.
 *
 * @param className - Additional CSS classes to merge with the header's default classes
 * @param props - Additional `div` props are spread onto the rendered header element
 * @returns The header container element for use inside a Card
 */
function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        '@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-1.5 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6',
        className
      )}
      {...props}
    />
  )
}

/**
 * Card title element displayed within a CardHeader.
 *
 * @param className - Additional CSS classes to apply to the title container.
 * @param props - Additional div attributes forwarded to the underlying element.
 * @returns The rendered div for the card title slot.
 */
function CardTitle({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-title"
      className={cn('leading-none font-semibold', className)}
      {...props}
    />
  )
}

/**
 * Renders the card description area.
 *
 * @returns A `div` configured as the card's description container.
 */
function CardDescription({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-description"
      className={cn('text-muted-foreground text-sm', className)}
      {...props}
    />
  )
}

/**
 * Action area within a Card for placing interactive controls aligned to the end of the header.
 *
 * @returns The card action container element (data-slot="card-action") with alignment classes to position controls at the header's end.
 */
function CardAction({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-action"
      className={cn('col-start-2 row-span-2 row-start-1 self-start justify-self-end', className)}
      {...props}
    />
  )
}

/**
 * Container for the card's main content area.
 *
 * Renders a div with data-slot="card-content", applies horizontal padding and any provided `className`, and forwards remaining div props.
 *
 * @returns A div element for the card's main content with merged className and forwarded props.
 */
function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div data-slot="card-content" className={cn('px-6', className)} {...props} />
}

/**
 * Footer area of a Card layout.
 *
 * Renders the card footer container with alignment and spacing classes and forwards any standard div props.
 *
 * @param className - Additional class names to merge with the component's default footer classes
 * @returns The rendered footer element configured with data-slot="card-footer" and layout/spacing classes
 */
function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="card-footer"
      className={cn('flex items-center px-6 [.border-t]:pt-6', className)}
      {...props}
    />
  )
}

export { Card, CardHeader, CardFooter, CardTitle, CardAction, CardDescription, CardContent }
