let csrf = "";
export const setCsrf = (value: string) => {
  csrf = value;
};
export async function api<T = Record<string, unknown>>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (init.method && !["GET", "HEAD"].includes(init.method))
    headers.set("X-CSRF-Token", csrf);
  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  if (response.status === 401 && path != "/api/auth/login") {
    window.dispatchEvent(new Event("session-expired"));
  }
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "So‘rovni tekshirib, qayta urinib ko‘ring.",
    );
  return data;
}
