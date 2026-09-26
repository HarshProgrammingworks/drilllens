import { useMemo, useState } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  TimeScale,
  Tooltip,
  CategoryScale,
} from "chart.js";
import zoomPlugin from "chartjs-plugin-zoom";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, TimeScale, zoomPlugin);

const COLORS = ["#d4a017", "#3d8bfd", "#3d9a6a", "#e07a2f", "#d64545", "#c4b5fd"];

export function ParameterChart({
  title,
  rows,
  xKey,
  series,
}: {
  title: string;
  rows: ReadonlyArray<object>;
  xKey: string;
  series: { key: string; label: string }[];
}) {
  const [hidden, setHidden] = useState<Record<string, boolean>>({});
  const labels = rows.map((row) => String((row as Record<string, unknown>)[xKey]));
  const data = useMemo(() => ({
    labels,
    datasets: series.filter((item) => !hidden[item.key]).map((item, index) => ({
      label: item.label,
      data: rows.map((row) => Number((row as Record<string, unknown>)[item.key])),
      borderColor: COLORS[index % COLORS.length],
      pointRadius: 0,
      tension: 0.15,
    })),
  }), [rows, series, hidden, labels]);

  return (
    <section className="panel p-3">
      <div className="flex items-center justify-between gap-2 mb-2">
        <h3 className="text-sm font-medium">{title}</h3>
        <div className="flex flex-wrap gap-1">
          {series.map((item) => (
            <button key={item.key} className={`text-[11px] border rounded px-1.5 py-0.5 ${hidden[item.key] ? "text-muted border-line" : "border-slate-400"}`} onClick={() => setHidden((prev) => ({ ...prev, [item.key]: !prev[item.key] }))}>
              {hidden[item.key] ? "Show" : "Hide"} {item.label}
            </button>
          ))}
        </div>
      </div>
      <div className="h-64">
        <Line
          data={data}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { labels: { color: "#c5d0dc" } },
              zoom: { zoom: { wheel: { enabled: true }, mode: "x" }, pan: { enabled: true, mode: "x" } },
            },
            scales: {
              x: { ticks: { color: "#93a4b8", maxTicksLimit: 6 }, grid: { color: "#243044" } },
              y: { ticks: { color: "#93a4b8" }, grid: { color: "#243044" } },
            },
          }}
        />
      </div>
    </section>
  );
}
