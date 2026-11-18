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
