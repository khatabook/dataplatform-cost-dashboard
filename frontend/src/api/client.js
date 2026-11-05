function defaultRange() {
  const end = new Date();
  end.setUTCDate(end.getUTCDate() - 1);
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - 27);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

export async function fetchJson(path, { from, to } = {}) {
  const range = { ...defaultRange(), ...(from && to ? { from, to } : {}) };
  const url = `${path}?from=${range.from}&to=${range.to}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

export { defaultRange };
