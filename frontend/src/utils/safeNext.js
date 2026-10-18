// Only allow in-app paths as a post-login redirect (blocks "//evil.com" and absolute URLs).
export const safeNext = (value) =>
  typeof value === "string" && value.startsWith("/") && !value.startsWith("//")
    ? value
    : null;

// Query string that carries the redirect (and a prefilled email) between Login and Register.
export const authQuery = (next, email) => {
  const p = new URLSearchParams();
  if (next) p.set("next", next);
  if (email) p.set("email", email);
  const s = p.toString();
  return s ? `?${s}` : "";
};
