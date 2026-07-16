// Thin fetch wrappers over the Nucleus API. No data-fetching library per the
// project's non-goals -- plain fetch + useState/useEffect in the components.

export async function fetchRawAlerts({ source = "synthetic", asOf } = {}) {
  const params = new URLSearchParams({ source });
  if (asOf != null) params.set("as_of", String(asOf));
  const res = await fetch(`/api/alerts/raw?${params}`);
  if (!res.ok) throw new Error(`raw alerts request failed: ${res.status}`);
  return res.json();
}

export async function fetchCorrelatedAlerts({
  source = "synthetic",
  alpha,
  beta,
  gamma,
  asOf,
} = {}) {
  const params = new URLSearchParams({ source });
  if (alpha != null) params.set("alpha", String(alpha));
  if (beta != null) params.set("beta", String(beta));
  if (gamma != null) params.set("gamma", String(gamma));
  if (asOf != null) params.set("as_of", String(asOf));
  const res = await fetch(`/api/alerts/correlated?${params}`);
  if (!res.ok) throw new Error(`correlated alerts request failed: ${res.status}`);
  return res.json();
}
