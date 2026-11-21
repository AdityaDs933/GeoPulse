const periodSelect = document.querySelector("#period-select");
const periodLabels = {
  7: "Last 7 days",
  30: "Last 30 days",
  90: "Last 90 days",
};

const periodMetrics = {
  7: { footfall: "24,892", area: "Downtown", peak: "5–6 PM", dwell: "18" },
  30: { footfall: "96,430", area: "Downtown", peak: "5–6 PM", dwell: "19" },
  90: { footfall: "281,705", area: "Riverside", peak: "4–5 PM", dwell: "17" },
};

const mapElement = document.querySelector("#activity-map");
const mapPanel = document.querySelector(".map-panel");
const mapExpandButton = document.querySelector(".map-expand");
let activityMap = null;

if (window.L && mapElement) {
  activityMap = L.map(mapElement, { scrollWheelZoom: false }).setView([18.5204, 73.8567], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(activityMap);

  [
    { name: "Shaniwar Wada", coordinates: [18.5195, 73.8553], level: "High", color: "#23876d", radius: 540 },
    { name: "Fergusson College Road", coordinates: [18.5236, 73.8415], level: "Medium", color: "#d4a449", radius: 390 },
    { name: "Koregaon Park", coordinates: [18.5362, 73.894], level: "Low", color: "#7e9eb6", radius: 300 },
  ].forEach(({ name, coordinates, level, color, radius }) => {
    L.circle(coordinates, {
      radius,
      color,
      fillColor: color,
      fillOpacity: 0.18,
      weight: 1,
    })
      .bindPopup(`<strong>${name}</strong>${level} illustrative activity<br>Demo marker · not measured data`)
      .addTo(activityMap);
  });
} else if (mapElement) {
  document.querySelector("#map-status").hidden = false;
}

mapExpandButton.addEventListener("click", () => {
  const expanded = mapPanel.classList.toggle("is-expanded");
  mapExpandButton.setAttribute("aria-expanded", String(expanded));
  mapExpandButton.setAttribute("aria-label", expanded ? "Collapse activity map" : "Expand activity map");
  if (activityMap) {
    window.requestAnimationFrame(() => activityMap.invalidateSize());
  }
});

periodSelect.addEventListener("change", (event) => {
  const selectedPeriod = event.currentTarget.value;
  const metrics = periodMetrics[selectedPeriod];

  document.querySelectorAll("[data-metric]").forEach((element) => {
    if (element.dataset.metric === "dwell") {
      element.firstChild.nodeValue = `${metrics.dwell} `;
    } else {
      element.textContent = metrics[element.dataset.metric];
    }
  });
  document.querySelector(".data-period").textContent = `· ${periodLabels[selectedPeriod]}`;
  document.querySelector(".chart-total").textContent = `${(Number(metrics.footfall.replace(",", "")) / 1000).toFixed(1)}k total`;
});

document.querySelector(".notice-close").addEventListener("click", () => {
  document.querySelector(".notice").hidden = true;
});

document.querySelector("#export-button").addEventListener("click", () => {
  const report = [
    "GeoPulse — Illustrative dashboard preview",
    `Reporting period: ${periodLabels[periodSelect.value]}`,
    `Total footfall: ${periodMetrics[periodSelect.value].footfall}`,
    `Busiest area: ${periodMetrics[periodSelect.value].area}`,
    `Peak activity: ${periodMetrics[periodSelect.value].peak}`,
    `Average dwell time: ${periodMetrics[periodSelect.value].dwell} minutes`,
    "",
    "Note: These figures are illustrative and are not based on a verified dataset.",
  ].join("\n");
  const link = document.createElement("a");
  const reportUrl = URL.createObjectURL(new Blob([report], { type: "text/plain" }));
  link.href = reportUrl;
  link.download = "geopulse-demo-report.txt";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(reportUrl), 1000);
});
