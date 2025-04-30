/**
 * Utility functions for the application
 */

/**
 * clsx implementation - combines multiple class names into a single string
 * Simplified version of the clsx library
 */
function clsx(...classes) {
  return classes.filter(Boolean).join(' ');
}

/**
 * Tailwind merge implementation - merges tailwind classes with proper precedence
 * Simplified version that doesn't handle all edge cases of the original library
 */
function twMerge(...classes) {
  // This is a very simplified version - in production, use the full tailwind-merge library
  return clsx(...classes);
}

/**
 * Combine multiple class names with proper tailwind precedence
 */
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Simple implementation of class-variance-authority
 */
function cva(base, config) {
  return (props) => {
    if (!props) return base;
    
    let className = base;
    
    // Add variant classes
    if (config.variants) {
      for (const [variant, options] of Object.entries(config.variants)) {
        const value = props[variant] || config.defaultVariants?.[variant];
        if (value != null && options[value]) {
          className = `${className} ${options[value]}`;
        }
      }
    }
    
    // Add additional classes
    if (props.className) {
      className = `${className} ${props.className}`;
    }
    
    return className;
  };
}

// Expose utilities to the window object so they can be used by components
window.clsx = clsx;
window.twMerge = twMerge;
window.cn = cn;
window.cva = cva; 