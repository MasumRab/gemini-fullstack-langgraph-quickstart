import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Combine multiple class-value inputs into one Tailwind-compatible class string.
 *
 * @param inputs - Class values (strings, arrays, objects, etc.) to be concatenated and resolved
 * @returns The final merged class string with Tailwind CSS class conflicts resolved
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
