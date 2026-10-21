import { alertText } from "../../utils/ganttFormat.js";

// Critical / warning messages straight from summary.alerts (the backend decides, the UI only shows).
export default function AlertBanner({ alerts, hasData }) {
  if (!alerts?.length) {
    if (!hasData) return null;
    return (
      <p className="text-sm text-success bg-success-soft border border-success/20 rounded-card px-4 py-3">
        Available funds currently cover all actual costs.
      </p>
    );
  }
  return (
    <div className="space-y-2" role="alert">
      {alerts.map((a) => (
        <p
          key={a.code}
          className={`text-sm rounded-card px-4 py-3 border ${
            a.level === "critical" ? "text-danger bg-danger-soft border-danger/20" : "text-warning bg-warning-soft border-warning/30"
          }`}
        >
          <span className="font-semibold">{a.level === "critical" ? "Critical: " : "Warning: "}</span>
          {alertText(a)}
        </p>
      ))}
    </div>
  );
}
