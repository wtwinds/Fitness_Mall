let chart = null;

function loadInsight(type, el) {

    // Highlight active
    document.querySelectorAll("#questionList button")
        .forEach(btn => btn.classList.remove("active"));

    if (el) el.classList.add("active");

    fetch(`/api/insight/${type}`)
        .then(res => res.json())
        .then(data => {

            const text = document.getElementById("textAnswer");
            const canvas = document.getElementById("chartCanvas");

            text.innerText = "";

            if (chart) chart.destroy();

            // TEXT ANSWER
            // TEXT
            if (data.type === "text") {
                text.innerText = data.value;
                return;
            }

            // CARD UI
            if (data.type === "card") {
                text.innerHTML = `
                    <div class="card shadow-sm p-3">
                        <h5 class="text-muted">${data.title}</h5>
                        <div class="display-5 fw-bold text-success">${data.value}</div>
                    </div>
                `;
                return;
            }

            // GRAPH
            if (data.type === "bar" || data.type === "pie") {

                const ctx = canvas.getContext("2d");

                chart = new Chart(ctx, {
                    type: data.type,
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: "Insight",
                            data: data.values,
                            borderWidth: 1,
                            backgroundColor: [
                                "#22c55e",
                                "#ef4444",
                                "#3b82f6",
                                "#f59e0b",
                                "#8b5cf6",
                                "#14b8a6",
                                "#f97316"
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        layout: { padding: 20 },
                        plugins: {
                            legend: {
                                position: "top",
                                labels: { font: { size: 14 } }
                            }
                        }
                    }
                });
            }
        });
}