declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

export function trackEvent(eventName: string, params?: Record<string, unknown>): void {
  if (typeof window.gtag !== "function") {
    return;
  }

  window.gtag("event", eventName, params);
}
