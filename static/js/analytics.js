(() => {
  const ENDPOINT = "/collect";
  const HEARTBEAT_MS = 15000;

  const sidKey = "zxt_analytics_sid";
  let sessionId = localStorage.getItem(sidKey);
  if (!sessionId) {
    sessionId = (crypto.randomUUID && crypto.randomUUID()) ||
      (`s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`);
    localStorage.setItem(sidKey, sessionId);
  }

  const path = location.pathname + (location.search || "");
  const started = Date.now();
  let maxVisible = 0;
  let visibleStarted = document.visibilityState === "visible" ? Date.now() : null;
  let sentLeave = false;

  const screenSize = `${window.screen?.width || 0}x${window.screen?.height || 0}`;

  function visibleMs() {
    let total = maxVisible;
    if (visibleStarted != null) total += Date.now() - visibleStarted;
    return Math.max(0, total);
  }

  function send(event, opts = {}) {
    const body = JSON.stringify({
      event,
      path: location.pathname || "/",
      session_id: sessionId,
      referrer: document.referrer || null,
      duration_ms: opts.duration_ms != null ? opts.duration_ms : visibleMs(),
      screen: screenSize,
    });
    try {
      if (opts.keepalive && navigator.sendBeacon) {
        const blob = new Blob([body], { type: "application/json" });
        navigator.sendBeacon(ENDPOINT, blob);
        return;
      }
      fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
        keepalive: !!opts.keepalive,
        credentials: "omit",
      }).catch(() => {});
    } catch (_) {
      /* ignore */
    }
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      if (visibleStarted != null) {
        maxVisible += Date.now() - visibleStarted;
        visibleStarted = null;
      }
      send("heartbeat", { keepalive: true });
    } else {
      visibleStarted = Date.now();
    }
  });

  window.addEventListener("pagehide", () => {
    if (sentLeave) return;
    sentLeave = true;
    send("leave", { keepalive: true });
  });

  send("pageview", { duration_ms: 0 });
  setInterval(() => {
    if (document.visibilityState === "visible") send("heartbeat");
  }, HEARTBEAT_MS);
})();
