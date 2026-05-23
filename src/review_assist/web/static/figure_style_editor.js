(function () {
  const HEX_COLOR = /^#[0-9A-Fa-f]{6}$/;
  const COLOR_NAMES = {
    "#1D4ED8": "Blue",
    "#2563EB": "Blue",
    "#00AAFF": "Blue",
    "#22C55E": "Wetland green",
    "#16A34A": "Green",
    "#0EA5E9": "Water blue",
    "#14B8A6": "Teal",
    "#A855F7": "Purple",
    "#F59E0B": "Amber",
    "#F97316": "Orange",
    "#EF4444": "Red",
    "#FFE500": "Yellow",
    "#111827": "Near black",
    "#6B7280": "Gray",
    "#FFFFFF": "White",
  };

  function updateColorControl(control) {
    const input = control.querySelector("[data-color-input]");
    const swatch = control.querySelector("[data-color-swatch]");
    const summary = control.querySelector("[data-color-summary]");
    const hint = control.querySelector("[data-color-hint]");
    if (!input || !swatch || !summary) {
      return;
    }

    const raw = input.value.trim();
    swatch.classList.remove("empty", "invalid");
    control.classList.remove("invalid");
    swatch.style.backgroundColor = "";
    input.setCustomValidity("");

    if (!raw) {
      swatch.classList.add("empty");
      summary.textContent = control.getAttribute("data-empty-label") || "None / default";
      if (hint) {
        hint.textContent = "Leave blank to use the generated default or no fill/stroke where applicable.";
      }
      return;
    }

    if (!HEX_COLOR.test(raw)) {
      swatch.classList.add("invalid");
      control.classList.add("invalid");
      summary.textContent = "Invalid color";
      input.setCustomValidity("Enter a color as #RRGGBB.");
      if (hint) {
        hint.textContent = "Enter a valid #RRGGBB hex color or leave blank for default.";
      }
      return;
    }

    const hex = raw.toUpperCase();
    swatch.style.backgroundColor = hex;
    summary.textContent = `${COLOR_NAMES[hex] || "Custom"} (${hex})`;
    if (hint) {
      hint.textContent = "Hex value retained for precision.";
    }
  }

  document.querySelectorAll("[data-color-control]").forEach((control) => {
    const input = control.querySelector("[data-color-input]");
    updateColorControl(control);
    if (input) {
      input.addEventListener("input", () => updateColorControl(control));
      input.addEventListener("change", () => updateColorControl(control));
    }
  });
})();
