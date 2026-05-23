(function () {
  const linesEl = document.getElementById("process-log-lines");
  const stateEl = document.getElementById("process-log-state");
  const refreshButton = document.getElementById("process-log-refresh");
  if (!linesEl || !stateEl) {
    return;
  }

  let pollTimer = null;

  async function refreshLog() {
    try {
      const response = await fetch("/api/logs?tail=50", {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      if (!response.ok) {
        throw new Error("log request failed");
      }
      const payload = await response.json();
      const lines = Array.isArray(payload.lines) ? payload.lines : [];
      linesEl.textContent = lines.length ? lines.join("\n") : "No process log entries yet.";
      linesEl.scrollTop = linesEl.scrollHeight;
      stateEl.textContent = payload.active ? "running" : "idle";
      stateEl.classList.toggle("running", Boolean(payload.active));
      setPolling(Boolean(payload.active));
    } catch (_error) {
      stateEl.textContent = "unavailable";
      stateEl.classList.remove("running");
    }
  }

  function setPolling(active) {
    if (active && pollTimer === null) {
      pollTimer = window.setInterval(refreshLog, 1500);
    }
    if (!active && pollTimer !== null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  async function submitProcessForm(event) {
    const form = event.currentTarget;
    if (!(form instanceof HTMLFormElement)) {
      return;
    }
    event.preventDefault();
    const action = form.getAttribute("data-process-action") || "process";
    stateEl.textContent = "running";
    stateEl.classList.add("running");
    setPolling(true);
    await refreshLog();

    try {
      const response = await fetch(form.action, {
        method: form.method || "POST",
        body: new FormData(form),
        credentials: "same-origin",
        redirect: "manual",
      });
      await refreshLog();
      const location = response.headers.get("Location");
      if (location) {
        window.location.href = location;
      } else {
        window.location.reload();
      }
    } catch (_error) {
      stateEl.textContent = "failed";
      stateEl.classList.remove("running");
      linesEl.textContent += `\n[client] ${action} request failed`;
      setPolling(false);
    }
  }

  if (refreshButton) {
    refreshButton.addEventListener("click", refreshLog);
  }
  document.querySelectorAll("form[data-process-form]").forEach((form) => {
    form.addEventListener("submit", submitProcessForm);
  });
  refreshLog();
})();
