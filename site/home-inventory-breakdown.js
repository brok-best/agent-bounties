// inventory-state-breakdown-v1 consumer.
// Counts come from one accepted canonical snapshot. Ready-to-earn stays
// gated on the existing isReadyToEarn / applied_view === "ready_to_earn"
// filter. This helper never relabels claimed, submitted, paid, degraded,
// or stale contracts as ready.
(function (root) {
  const SCHEMA = "inventory-state-breakdown-v1";
  const MAX_AGE_SECONDS = 900;

  function parseStamp(value) {
    const ms = Date.parse(value);
    return Number.isFinite(ms) ? ms : null;
  }

  function consumeInventoryBreakdown(snapshot, readyProjection, nowMs) {
    const generatedAt = parseStamp(snapshot && snapshot.generated_at);
    const source = (snapshot && snapshot.source) || {};
    const degraded = Boolean(source.degraded) || source.available === false;
    const stale = generatedAt == null || (nowMs - generatedAt) / 1000 > MAX_AGE_SECONDS;
    const readyItems = (readyProjection && readyProjection.items) || [];
    const readyGateFailed = !readyProjection
      || readyProjection.applied_view !== "ready_to_earn"
      || readyProjection.degraded
      || degraded
      || stale;
    return {
      schema: SCHEMA,
      generated_at: snapshot && snapshot.generated_at,
      source: source,
      stale: stale,
      source_degraded: degraded,
      ready_to_earn: readyGateFailed ? 0 : readyItems.length,
      in_progress: Number((snapshot && snapshot.counts && snapshot.counts.in_progress) || 0),
      submitted: Number((snapshot && snapshot.counts && snapshot.counts.submitted) || 0),
      paid: Number((snapshot && snapshot.counts && snapshot.counts.paid) || 0),
      verification_unavailable: Number((snapshot && snapshot.counts && snapshot.counts.verification_unavailable) || 0)
    };
  }

  root.consumeInventoryBreakdown = consumeInventoryBreakdown;
})(typeof window !== "undefined" ? window : globalThis);
