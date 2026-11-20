export async function readResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({})) as { detail?: string }
  if (!response.ok) throw new Error(payload.detail ?? `Request failed (${response.status}).`)
  return payload as T
}
