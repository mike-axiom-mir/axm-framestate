"use strict";

(function () {
  const cloneValue = (value) => JSON.parse(JSON.stringify(value));

  function formatElapsed(ms) {
    const total = Math.max(0, Math.floor(Number(ms) || 0));
    const seconds = Math.floor(total / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;
    if (minutes < 60) return `${minutes}m ${String(rest).padStart(2, "0")}s`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${String(minutes % 60).padStart(2, "0")}m`;
  }

  function shortDigest(value) {
    return String(value || "").replace(/^sha256:/, "").slice(0, 12) || "pending";
  }

  function newRenderSession(project, digest, mode, startedAt = Date.now()) {
    return {
      status: "running",
      project: cloneValue(project),
      digest,
      mode,
      name: `${project.id}-${shortDigest(digest)}`,
      startedAt,
      output: null,
      receipt: null,
      error: null,
    };
  }

  function renderSessionView(session, now = Date.now(), currentDirty = false, currentDigest = "") {
    if (!session) return {
      state: "READY",
      tone: "idle",
      elapsed: "idle",
      detail: "Final Render validates the current project, then renders a fixed canonical snapshot. Rendering never saves edits automatically.",
      snapshot: "created on start",
      mode: "—",
      receipt: "none",
      retry: false,
    };

    const elapsed = formatElapsed(Math.max(0, Number(now) - Number(session.startedAt || now)));
    const currentMoved = !!currentDirty || (!!currentDigest && currentDigest !== session.digest);
    const editNote = currentMoved ? " Current Studio edits may be newer; this render remains bound to the submitted snapshot." : "";

    if (session.status === "running") return {
      state: "RENDERING LOCAL SNAPSHOT",
      tone: "running",
      elapsed,
      detail: `Waiting for the local renderer. No percentage is shown because the current API does not expose truthful progress.${editNote}`,
      snapshot: shortDigest(session.digest),
      mode: String(session.mode || "exact").toUpperCase(),
      receipt: "waiting",
      retry: false,
    };

    if (session.status === "complete") return {
      state: "COMPLETION RECEIPT RECEIVED",
      tone: "complete",
      elapsed,
      detail: `The renderer returned a completion receipt for this submitted snapshot.${editNote}`,
      snapshot: shortDigest(session.digest),
      mode: String(session.mode || "exact").toUpperCase(),
      receipt: "received",
      retry: false,
    };

    return {
      state: "NO COMPLETION RECEIPT",
      tone: "held",
      elapsed,
      detail: `The request ended with an error before Studio received a completion receipt. Do not infer that output completed or failed from the missing receipt. Retry Same Snapshot preserves the submitted project, digest, mode, and digest-derived checkpoint path.${editNote}`,
      snapshot: shortDigest(session.digest),
      mode: String(session.mode || "exact").toUpperCase(),
      receipt: "none",
      retry: true,
    };
  }

  const helpers = { formatElapsed, shortDigest, newRenderSession, renderSessionView };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = helpers;
    return;
  }

  let active = null;
  let clock = null;
  const renderButton = document.querySelector("#renderBtn");
  const retryButton = document.querySelector("#retryRenderBtn");

  function draw() {
    const host = document.querySelector("#renderSession");
    if (!host) return;
    const view = renderSessionView(active, Date.now(), S.dirty, S.digest);
    host.dataset.state = view.tone;
    document.querySelector("#renderSessionState").textContent = view.state;
    document.querySelector("#renderElapsed").textContent = view.elapsed;
    document.querySelector("#renderSessionDetail").textContent = view.detail;
    document.querySelector("#renderSnapshot").textContent = view.snapshot;
    document.querySelector("#renderMode").textContent = view.mode;
    document.querySelector("#renderReceipt").textContent = view.receipt;
    retryButton.hidden = !view.retry;
    retryButton.disabled = !view.retry || active?.status === "running";
  }

  function stopClock() {
    clearInterval(clock);
    clock = null;
  }

  function startClock() {
    stopClock();
    clock = setInterval(draw, 250);
  }

  async function submit(session) {
    active = session;
    renderButton.disabled = true;
    renderButton.textContent = "Rendering…";
    draw();
    startClock();
    try {
      const result = await api("/api/render", {
        project: session.project,
        name: session.name,
        profile: "h264",
        mode: session.mode,
      });
      session.status = "complete";
      session.output = result.output || null;
      session.receipt = result;
      document.querySelector("#evidence").textContent = JSON.stringify(result, null, 2);
      toast(`Render complete: ${result.output}`);
    } catch (error) {
      session.status = "no_receipt";
      session.error = error.message;
      document.querySelector("#evidence").textContent = JSON.stringify({
        display_only: "FrameState Studio render request",
        snapshot_digest: session.digest,
        mode: session.mode,
        completion_receipt: "NONE",
        error: error.message,
      }, null, 2);
      toast(`Render request ended: ${error.message}`, true);
    } finally {
      stopClock();
      draw();
      renderButton.disabled = false;
      renderButton.textContent = "Render Final";
    }
  }

  async function beginFinalRender() {
    if (!await normalizeProject(false)) return;
    const mode = document.querySelector("#realizationMode").value;
    await submit(newRenderSession(S.project, S.digest, mode));
  }

  async function retrySameSnapshot() {
    if (!active || active.status !== "no_receipt") return;
    const retry = {
      ...active,
      status: "running",
      project: cloneValue(active.project),
      startedAt: Date.now(),
      output: null,
      receipt: null,
      error: null,
    };
    await submit(retry);
  }

  renderButton.onclick = beginFinalRender;
  retryButton.onclick = retrySameSnapshot;
  document.addEventListener("input", draw, true);
  document.addEventListener("change", draw, true);
  document.addEventListener("click", () => setTimeout(draw, 0), true);
  draw();
})();
