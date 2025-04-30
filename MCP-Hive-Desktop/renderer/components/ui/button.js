/**
 * Button Component
 * Based on shadcn/ui Button component
 */

// Import the necessary utilities
const { cva } = window.cva;
const { cn } = window.cn;

// Button variant definitions
const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

/**
 * Creates a button element with specified attributes and children
 */
function Button({ className, variant, size, asChild = false, ...props }) {
  // Create element
  const element = document.createElement("button");
  
  // Apply classes
  element.className = cn(buttonVariants({ variant, size, className }));
  
  // Add additional properties
  for (const [key, value] of Object.entries(props)) {
    // Handle event listeners (properties starting with 'on')
    if (key.startsWith('on') && typeof value === 'function') {
      const eventName = key.substring(2).toLowerCase();
      element.addEventListener(eventName, value);
    } 
    // Handle attributes
    else if (key !== 'children') {
      element.setAttribute(key, value);
    }
  }
  
  // Add children if present
  if (props.children) {
    if (typeof props.children === 'string') {
      element.textContent = props.children;
    } else if (Array.isArray(props.children)) {
      props.children.forEach(child => {
        if (typeof child === 'string') {
          element.appendChild(document.createTextNode(child));
        } else if (child instanceof Node) {
          element.appendChild(child);
        }
      });
    } else if (props.children instanceof Node) {
      element.appendChild(props.children);
    }
  }
  
  return element;
}

// Export the button functions
window.Button = Button;
window.buttonVariants = buttonVariants; 