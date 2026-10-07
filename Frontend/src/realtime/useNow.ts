import { useCallback, useSyncExternalStore } from 'react';

const subscriptions = new Map<() => void, { interval: number; emitted: number }>();
let now = Date.now();
let timer: ReturnType<typeof setInterval> | undefined;

function publish(force = false) {
  now = Date.now();
  for (const [listener, entry] of subscriptions) {
    if (force || now - entry.emitted >= entry.interval) {
      entry.emitted = now;
      listener();
    }
  }
}

function reschedule() {
  clearInterval(timer);
  timer = undefined;
  if (document.hidden || !subscriptions.size) return;
  const interval = Math.min(...[...subscriptions.values()].map(entry => entry.interval));
  timer = setInterval(publish, interval);
}

function visibility() {
  reschedule();
  if (!document.hidden) publish(true);
}

/** All countdowns share one clock; pause hidden tabs and resync on return. */
export function useNow(intervalMs = 30_000): number {
  const subscribe = useCallback((listener: () => void) => {
    if (!subscriptions.size) document.addEventListener('visibilitychange', visibility);
    subscriptions.set(listener, { interval: intervalMs, emitted: 0 });
    reschedule();
    publish(true);
    return () => {
      subscriptions.delete(listener);
      if (!subscriptions.size) document.removeEventListener('visibilitychange', visibility);
      reschedule();
    };
  }, [intervalMs]);
  return useSyncExternalStore(subscribe, () => now, () => now);
}
