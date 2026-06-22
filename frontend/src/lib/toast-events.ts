/**
 * Lightweight event bridge between api.ts and the React ToastProvider.
 *
 * api.ts fires plain DOM custom events on `window`; ToastProvider listens
 * for them and calls `addToast`. This keeps the request layer free of
 * React hook dependencies.
 */

export type ApiErrorEventDetail = {
  message: string;
  /** If provided, getToastProvider callback will add a retry action */
  actionLabel?: string;
  actionOnClick?: () => void;
};

export function emitApiError(detail: ApiErrorEventDetail) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<ApiErrorEventDetail>("toast:api-error", { detail }),
  );
}
