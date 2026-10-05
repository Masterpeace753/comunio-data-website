const LOCAL_ORIGIN = "http://next.local";

/**
 * Accept only same-origin, root-relative destinations for post-login redirects.
 * A fallback is returned for absolute URLs, protocol-relative URLs, and malformed input.
 */
export function safeRedirectPath(value: unknown, fallback = "/"): string {
  const safeFallback = isSafePath(fallback) ? fallback : "/";
  return isSafePath(value) ? value : safeFallback;
}

export function loginUrlFor(value: unknown): string {
  const query = new URLSearchParams({
    next: safeRedirectPath(value),
  });
  return `/login?${query.toString()}`;
}

function isSafePath(value: unknown): value is string {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\") ||
    /[\u0000-\u001f\u007f]/.test(value)
  ) {
    return false;
  }

  try {
    const url = new URL(value, LOCAL_ORIGIN);
    return url.origin === LOCAL_ORIGIN && !url.username && !url.password;
  } catch {
    return false;
  }
}
