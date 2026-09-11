export async function httpErrorMessage(res) {
  let msg = `HTTP ${res.status}`
  try {
    const body = await res.json()
    if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)
  } catch {}
  return msg
}

export async function jfetch(url, opts = {}) {
  const res = await fetch(url, opts)
  if (!res.ok) throw new Error(await httpErrorMessage(res))
  return res.json()
}