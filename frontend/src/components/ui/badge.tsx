import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

// DESIGN.md — tiny inline tags only get {rounded.xs} (2px); everything stays flat.
const badgeVariants = cva(
  "group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-[2px] border border-transparent px-2 py-0.5 text-[10px] font-semibold tracking-wide whitespace-nowrap transition-colors focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 aria-invalid:border-destructive aria-invalid:ring-destructive/20 [&>svg]:pointer-events-none [&>svg]:size-3!",
  {
    variants: {
      variant: {
        // signal-live — white glyph on red field
        default: "bg-red text-white [a]:hover:bg-red-deep",
        secondary:
          "bg-gray-100 text-ink-soft [a]:hover:bg-gray-200",
        destructive:
          "bg-red text-white focus-visible:ring-red-deep/20 [a]:hover:bg-red-deep",
        // signal-dormant — faint ink
        outline:
          "border-hairline text-ink [a]:hover:bg-gray-100 [a]:hover:text-ink",
        ghost:
          "hover:bg-gray-100 hover:text-ink",
        link: "text-red underline-offset-4 hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  })
}

export { Badge, badgeVariants }
