(function () {
  const linesEl = document.getElementById("process-log-lines");
  const stateEl = document.getElementById("process-log-state");
  const refreshButton = document.getElementById("process-log-refresh");
  const resizeHandle = document.getElementById("process-log-resizer");
  if (!linesEl || !stateEl) {
    return;
  }

  let pollTimer = null;
  const storageKey = "reviewAssist.processLogHeight";
  const defaultHeight = 150;

  function clampHeight(value) {
    const maxHeight = Math.max(120, Math.min(window.innerHeight * 0.7, window.innerHeight - 120));
    return Math.min(Math.max(value, 90), maxHeight);
  }

  function setLogHeight(value) {
    const height = Math.round(clampHeight(value));
    document.documentElement.style.setProperty("--process-log-lines-height", `${height}px`);
    if (resizeHandle) {
      resizeHandle.setAttribute("aria-valuenow", String(height));
    }
    try {
      window.localStorage.setItem(storageKey, String(height));
    } catch (_error) {
      // Local storage is optional; resizing still works for the current page.
    }
  }

  function savedLogHeight() {
    try {
      return Number.parseInt(window.localStorage.getItem(storageKey) || "", 10);
    } catch (_error) {
      return Number.NaN;
    }
  }

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
    refreshButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      refreshLog();
    });
  }
  if (resizeHandle) {
    resizeHandle.setAttribute("aria-valuemin", "90");
    resizeHandle.setAttribute("aria-valuemax", String(Math.round(clampHeight(window.innerHeight))));
    setLogHeight(Number.isFinite(savedLogHeight()) ? savedLogHeight() : defaultHeight);
    resizeHandle.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      resizeHandle.setPointerCapture(event.pointerId);
      const startY = event.clientY;
      const startHeight = linesEl.getBoundingClientRect().height;

      function drag(moveEvent) {
        setLogHeight(startHeight + startY - moveEvent.clientY);
      }

      function stop(upEvent) {
        resizeHandle.releasePointerCapture(upEvent.pointerId);
        resizeHandle.removeEventListener("pointermove", drag);
        resizeHandle.removeEventListener("pointerup", stop);
        resizeHandle.removeEventListener("pointercancel", stop);
      }

      resizeHandle.addEventListener("pointermove", drag);
      resizeHandle.addEventListener("pointerup", stop);
      resizeHandle.addEventListener("pointercancel", stop);
    });
    resizeHandle.addEventListener("dblclick", () => setLogHeight(defaultHeight));
    resizeHandle.addEventListener("keydown", (event) => {
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setLogHeight(linesEl.getBoundingClientRect().height + 20);
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setLogHeight(linesEl.getBoundingClientRect().height - 20);
      }
      if (event.key === "Home") {
        event.preventDefault();
        setLogHeight(90);
      }
      if (event.key === "End") {
        event.preventDefault();
        setLogHeight(window.innerHeight);
      }
    });
    window.addEventListener("resize", () => {
      resizeHandle.setAttribute("aria-valuemax", String(Math.round(clampHeight(window.innerHeight))));
      setLogHeight(linesEl.getBoundingClientRect().height);
    });
  }
  document.querySelectorAll("form[data-process-form]").forEach((form) => {
    form.addEventListener("submit", submitProcessForm);
  });
  refreshLog();
})();
