/**
 * Card Component
 * Based on shadcn/ui Card component
 */

const { cn } = window.cn;

/**
 * Creates a card container element
 */
function Card({ className, ...props }) {
  const element = document.createElement("div");
  element.className = cn(
    "rounded-lg border bg-card text-card-foreground shadow-sm",
    className
  );
  
  // Add additional properties
  for (const [key, value] of Object.entries(props)) {
    // Handle event listeners
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

/**
 * Creates a card header element
 */
function CardHeader({ className, ...props }) {
  const element = document.createElement("div");
  element.className = cn("flex flex-col space-y-1.5 p-6", className);
  
  // Add additional properties and children
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith('on') && typeof value === 'function') {
      const eventName = key.substring(2).toLowerCase();
      element.addEventListener(eventName, value);
    } else if (key !== 'children') {
      element.setAttribute(key, value);
    }
  }
  
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

/**
 * Creates a card title element
 */
function CardTitle({ className, ...props }) {
  const element = document.createElement("h3");
  element.className = cn("text-lg font-semibold leading-none tracking-tight", className);
  
  // Add additional properties and children
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith('on') && typeof value === 'function') {
      const eventName = key.substring(2).toLowerCase();
      element.addEventListener(eventName, value);
    } else if (key !== 'children') {
      element.setAttribute(key, value);
    }
  }
  
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

/**
 * Creates a card description element
 */
function CardDescription({ className, ...props }) {
  const element = document.createElement("p");
  element.className = cn("text-sm text-muted-foreground", className);
  
  // Add additional properties and children
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith('on') && typeof value === 'function') {
      const eventName = key.substring(2).toLowerCase();
      element.addEventListener(eventName, value);
    } else if (key !== 'children') {
      element.setAttribute(key, value);
    }
  }
  
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

/**
 * Creates a card content element
 */
function CardContent({ className, ...props }) {
  const element = document.createElement("div");
  element.className = cn("p-6 pt-0", className);
  
  // Add additional properties and children
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith('on') && typeof value === 'function') {
      const eventName = key.substring(2).toLowerCase();
      element.addEventListener(eventName, value);
    } else if (key !== 'children') {
      element.setAttribute(key, value);
    }
  }
  
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

/**
 * Creates a card footer element
 */
function CardFooter({ className, ...props }) {
  const element = document.createElement("div");
  element.className = cn("flex items-center p-6 pt-0", className);
  
  // Add additional properties and children
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith('on') && typeof value === 'function') {
      const eventName = key.substring(2).toLowerCase();
      element.addEventListener(eventName, value);
    } else if (key !== 'children') {
      element.setAttribute(key, value);
    }
  }
  
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

// Export the card component functions
window.Card = Card;
window.CardHeader = CardHeader;
window.CardTitle = CardTitle;
window.CardDescription = CardDescription;
window.CardContent = CardContent;
window.CardFooter = CardFooter; 