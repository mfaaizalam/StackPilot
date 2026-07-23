import { useEffect, useRef } from "react";

/**
 * Attaches an IntersectionObserver to the returned ref and adds
 * "is-visible" (paired with the .reveal CSS class) once the element
 * scrolls into the viewport. Unobserves after first reveal.
 */
export default function useReveal(options = {}) {
  const ref = useRef(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, ...options }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return ref;
}
