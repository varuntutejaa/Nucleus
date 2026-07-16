import { useEffect, useRef, useState } from "react";

const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Animates a displayed integer toward `target` over `duration` ms using an
// ease-out curve. Jumps instantly if the user prefers reduced motion.
export function useAnimatedNumber(target, duration = 900) {
  const [value, setValue] = useState(target);
  const frame = useRef(null);
  const from = useRef(target);

  useEffect(() => {
    if (prefersReducedMotion() || target == null) {
      setValue(target ?? 0);
      return;
    }
    const start = performance.now();
    const startValue = from.current;
    const delta = target - startValue;

    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(Math.round(startValue + delta * eased));
      if (t < 1) {
        frame.current = requestAnimationFrame(tick);
      } else {
        from.current = target;
      }
    }
    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration]);

  return value;
}
