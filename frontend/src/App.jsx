import React, { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";

// === Config ===
const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// === Pequeños helpers de estilo ===
const colors = {
  blueBg1: "#0ea5e9", // sky-500
  blueBg2: "#0b5ed7", // primary-ish
  surface: "rgba(255,255,255,0.90)",
  outline: "rgba(0,0,0,.08)",
  text: "#0f172a",
  sub: "#475569",
  ok: "#16a34a",
  warn: "#f59e0b",
  hi: "#ef4444",
};

const Card = ({ title, right = null, children, style }) => (
  <section
    style={{
      background: colors.surface,
      border: `1px solid ${colors.outline}`,
      borderRadius: 20,
      padding: 18,
      boxShadow: "0 12px 40px rgba(2, 6, 23, .12)",
      ...style,
    }}
  >
    <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
      {title ? (
        <h2 style={{ margin: 0, fontSize: 18, color: colors.text }}>{title}</h2>
      ) : (
        <span />
      )}
      <div style={{ marginLeft: "auto" }}>{right}</div>
    </div>
    {children}
  </section>
);

const TabButton = ({ active, children, onClick }) => (
  <button
    onClick={onClick}
    style={{
      padding: "10px 14px",
      borderRadius: 12,
      border: `1px solid ${active ? "transparent" : colors.outline}`,
      background: active
        ? "linear-gradient(135deg, #111827, #1f2937)"
        : "#ffffff",
      color: active ? "#fff" : colors.text,
      fontWeight: 700,
      letterSpacing: 0.2,
      boxShadow: active ? "0 8px 22px rgba(17,24,39,.25)" : "none",
      cursor: "pointer",
    }}
  >
    {children}
  </button>
);

const PrimaryBtn = ({ children, ...props }) => (
  <button
    {...props}
    style={{
      padding: "10px 14px",
      borderRadius: 12,
      border: "none",
      background: "linear-gradient(135deg, #2563eb, #0ea5e9)",
      color: "#fff",
      fontWeight: 800,
      letterSpacing: 0.3,
      cursor: "pointer",
      boxShadow: "0 10px 30px rgba(37,99,235,.35)",
    }}
  >
    {children}
  </button>
);

// === Branding simple ===
const Logo = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
    <div
      aria-hidden
      style={{
        width: 40,
        height: 40,
        borderRadius: 12,
        background: "linear-gradient(135deg, #22d3ee, #3b82f6)",
        display: "grid",
        placeItems: "center",
        boxShadow: "0 10px 30px rgba(59,130,246,.35)",
      }}
    >
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z" fill="#fff" />
      </svg>
    </div>
    <div>
      <div style={{ fontWeight: 900, fontSize: 22, color: "#fff" }}>Fire Risk</div>
      <div style={{ color: "#e2e8f0", fontSize: 12 }}>Tunja · ML + Datos Climáticos</div>
    </div>
  </div>
);

// === Widgets ===
function RiskBadge({ p }) {
  const pct = (p * 100).toFixed(2);
  let color = colors.ok,
    text = "Bajo";
  if (p >= 0.8) {
    color = colors.hi;
    text = "Muy alto";
  } else if (p > 0.5) {
    color = "#dc2626";
    text = "Alto";
  } else if (p >= 0.2) {
    color = colors.warn;
    text = "Moderado";
  }
  return (
    <div
      style={{
        display: "inline-block",
        padding: "8px 12px",
        borderRadius: 999,
        background: color,
        color: "#fff",
        fontWeight: 800,
      }}
    >
      {text} · {pct}%
    </div>
  );
}

const Radial = ({ p }) => {
  const pct = Math.max(0, Math.min(100, p * 100));
  const r = 58;
  const c = 2 * Math.PI * r;
  const off = c - (pct / 100) * c;
  const color = p >= 0.8 ? colors.hi : p > 0.5 ? "#dc2626" : p >= 0.2 ? colors.warn : colors.ok;
  return (
    <svg width={160} height={160} viewBox="0 0 160 160">
      <defs>
        <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" />
        </filter>
      </defs>
      <circle cx={80} cy={80} r={r} stroke="#e2e8f0" strokeWidth={14} fill="none" />
      <circle
        cx={80}
        cy={80}
        r={r}
        stroke={color}
        strokeWidth={14}
        strokeLinecap="round"
        fill="none"
        strokeDasharray={c}
        strokeDashoffset={off}
        style={{ filter: "url(#soft)" }}
      />
      <text x="80" y="78" textAnchor="middle" fontSize="28" fontWeight="900" fill={colors.text}>
        {pct.toFixed(1)}%
      </text>
      <text x="80" y="102" textAnchor="middle" fontSize="12" fill={colors.sub}>
        probabilidad
      </text>
    </svg>
  );
};

// === App ===
export default function App() {
  const [tab, setTab] = useState("hist");
  const [cities, setCities] = useState(["tunja"]);
  const [city, setCity] = useState("tunja");

  const [days, setDays] = useState([]);
  const [selectedDay, setSelectedDay] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const [manual, setManual] = useState({ tmax: "", tmin: "", humidity: "", wind: "", rain_24h: "" });
  const [range, setRange] = useState({ start: "", end: "" });
  const [series, setSeries] = useState([]);

  const [apiKey, setApiKey] = useState(localStorage.getItem("X_API_KEY") || "");
  const [toast, setToast] = useState("");

  // Localidades
  useEffect(() => {
    fetch(`${API_BASE}/locations`)
      .then((r) => r.json())
      .then((j) => {
        const cs = j.locations?.length ? j.locations : ["tunja"];
        setCities(cs);
        setCity(cs[0]);
      })
      .catch(() => {});
  }, []);

  // Días por ciudad
  useEffect(() => {
    if (!city) return;
    fetch(`${API_BASE}/days?city=${encodeURIComponent(city)}`)
      .then((r) => r.json())
      .then((j) => {
        setDays(j.dates || []);
        setSelectedDay(j.dates?.[j.dates.length - 1] || "");
      })
      .catch(() => {});
  }, [city]);

  const fetchByDate = async () => {
    if (!selectedDay) return;
    setLoading(true);
    setResult(null);
    const r = await fetch(`${API_BASE}/predict/by-date?date=${selectedDay}&city=${encodeURIComponent(city)}`);
    const j = await r.json();
    setResult(j);
    setLoading(false);
  };

  const fetchManual = async () => {
    const body = {
      date: new Date().toISOString().slice(0, 10),
      tmax: Number(manual.tmax),
      tmin: Number(manual.tmin),
      humidity: Number(manual.humidity),
      wind: Number(manual.wind),
      rain_24h: manual.rain_24h === "" ? null : Number(manual.rain_24h),
      rain_7d: null,
      rain_30d: null,
    };
    setLoading(true);
    setResult(null);
    const r = await fetch(`${API_BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    setResult(j);
    setLoading(false);
  };

  const fetchRange = async () => {
    if (!range.start || !range.end) return;
    setLoading(true);
    setSeries([]);
    const r = await fetch(
      `${API_BASE}/predict/range?start=${range.start}&end=${range.end}&city=${encodeURIComponent(city)}`
    );
    const j = await r.json();
    setSeries(j.points || []);
    setLoading(false);
  };

  const doTrain = async () => {
    const key = apiKey || window.prompt("API key de administrador:");
    if (!key) return;
    setApiKey(key);
    localStorage.setItem("X_API_KEY", key);
    setLoading(true);
    const r = await fetch(`${API_BASE}/train`, { method: "POST", headers: { "X-API-Key": key } });
    const j = await r.json();
    setLoading(false);
    if (r.ok) {
      setToast("Modelo re-entrenado correctamente");
      setTimeout(() => setToast(""), 2500);
    } else {
      alert("Error: " + (j?.detail || JSON.stringify(j)));
    }
  };

  const chartData = useMemo(
    () => (series || []).map((p) => ({ date: p.date, prob: +(p.probability * 100).toFixed(3) })),
    [series]
  );

  const Loader = (
    <div style={{ padding: 12, color: colors.sub, fontWeight: 600, letterSpacing: 0.3 }}>Cargando…</div>
  );

  return (
    <div
      style={{
        minHeight: "100vh",
        background: `radial-gradient(1200px 600px at 50% -100px, rgba(255,255,255,.25), transparent 60%), linear-gradient(180deg, ${
          colors.blueBg1
        } 0%, ${colors.blueBg2} 100%)`,
        padding: 24,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
      }}
    >
      <div style={{ width: "100%", maxWidth: 1120 }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 18,
          }}
        >
          <Logo />
          <div style={{ display: "flex", gap: 10 }}>
            <TabButton active={tab === "hist"} onClick={() => setTab("hist")}>Histórico</TabButton>
            <TabButton active={tab === "manual"} onClick={() => setTab("manual")}>Simulador</TabButton>
            <TabButton active={tab === "serie"} onClick={() => setTab("serie")}>Serie</TabButton>
            <PrimaryBtn onClick={doTrain} title="Solo admin">Re-entrenar</PrimaryBtn>
          </div>
        </div>

        {/* Selector de localidad */}
        <Card title="Localidad">
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            style={{
              padding: 12,
              borderRadius: 12,
              border: `1px solid ${colors.outline}`,
              minWidth: 240,
              fontWeight: 700,
            }}
          >
            {cities.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </Card>

        {/* HISTÓRICO */}
        {tab === "hist" && (
          <>
            <Card
              title="Selecciona una fecha del histórico"
              right={
                <PrimaryBtn onClick={fetchByDate} disabled={!selectedDay || loading}>
                  {loading ? "Cargando…" : "Predecir"}
                </PrimaryBtn>
              }
            >
              <select
                value={selectedDay}
                onChange={(e) => setSelectedDay(e.target.value)}
                style={{ padding: 12, borderRadius: 12, border: `1px solid ${colors.outline}`, minWidth: 260 }}
              >
                {days.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </Card>

            {result && (
              <Card
                title={`Resultado para ${result?.analyzed_data?.date} (${city})`}
                right={<RiskBadge p={result.probability || 0} />}
              >
                <div style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap" }}>
                  <Radial p={result.probability || 0} />
                  <div>
                    <div style={{ color: colors.sub, marginBottom: 6 }}>Datos analizados</div>
                    <pre
                      style={{
                        background: "#f8fafc",
                        padding: 12,
                        borderRadius: 12,
                        maxHeight: 220,
                        overflow: "auto",
                        border: `1px solid ${colors.outline}`,
                      }}
                    >
                      {JSON.stringify(result.analyzed_data, null, 2)}
                    </pre>
                  </div>
                  {result.chart_png_base64 && (
                    <div style={{ marginLeft: "auto" }}>
                      <img
                        alt="prob chart"
                        style={{ maxWidth: 280, borderRadius: 12, border: `1px solid ${colors.outline}` }}
                        src={`data:image/png;base64,${result.chart_png_base64}`}
                      />
                    </div>
                  )}
                </div>
                <div style={{ color: colors.sub, fontSize: 12, marginTop: 10 }}>
                  Referencias: Bajo 0–20%, Moderado 20–50%, Alto 50–80%, Muy alto 80–100%
                </div>
              </Card>
            )}

            {loading && Loader}
          </>
        )}

        {/* SIMULADOR */}
        {tab === "manual" && (
          <Card title="Simulador (ingresa valores diarios)">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
              {[
                ["tmax", "Tmax (°C)", "number"],
                ["tmin", "Tmin (°C)", "number"],
                ["humidity", "Humedad (%)", "number"],
                ["wind", "Viento (km/h)", "number"],
                ["rain_24h", "Lluvia 24h (mm) – opcional", "number"],
              ].map(([k, label, type]) => (
                <label key={k} style={{ display: "flex", flexDirection: "column", fontSize: 14 }}>
                  {label}
                  <input
                    type={type}
                    value={manual[k]}
                    onChange={(e) => setManual((v) => ({ ...v, [k]: e.target.value }))}
                    style={{ padding: 12, borderRadius: 12, border: `1px solid ${colors.outline}` }}
                  />
                </label>
              ))}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 14 }}>
              <PrimaryBtn onClick={fetchManual} disabled={loading}>
                {loading ? "Calculando…" : "Predecir"}
              </PrimaryBtn>
              {result && <RiskBadge p={result.probability || 0} />}
            </div>

            {result && (
              <div style={{ marginTop: 14, display: "flex", gap: 18, flexWrap: "wrap" }}>
                <Radial p={result.probability || 0} />
                {result.chart_png_base64 && (
                  <img
                    alt="prob chart"
                    style={{ maxWidth: 260, borderRadius: 12, border: `1px solid ${colors.outline}` }}
                    src={`data:image/png;base64,${result.chart_png_base64}`}
                  />
                )}
                <pre
                  style={{
                    background: "#f8fafc",
                    padding: 12,
                    borderRadius: 12,
                    maxHeight: 220,
                    overflow: "auto",
                    border: `1px solid ${colors.outline}`,
                  }}
                >
                  {JSON.stringify(result.analyzed_data, null, 2)}
                </pre>
            </div>
            )}

            {loading && Loader}
          </Card>
        )}

        {/* SERIE */}
        {tab === "serie" && (
          <>
            <Card
              title="Rango de fechas"
              right={
                <PrimaryBtn onClick={fetchRange} disabled={loading || !range.start || !range.end}>
                  {loading ? "Cargando…" : "Calcular serie"}
                </PrimaryBtn>
              }
            >
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <label>
                  Inicio
                  <input
                    type="date"
                    value={range.start}
                    onChange={(e) => setRange((v) => ({ ...v, start: e.target.value }))}
                    style={{ marginLeft: 8, padding: 12, borderRadius: 12, border: `1px solid ${colors.outline}` }}
                  />
                </label>
                <label>
                  Fin
                  <input
                    type="date"
                    value={range.end}
                    onChange={(e) => setRange((v) => ({ ...v, end: e.target.value }))}
                    style={{ marginLeft: 8, padding: 12, borderRadius: 12, border: `1px solid ${colors.outline}` }}
                  />
                </label>
              </div>
            </Card>

            {!!series.length && (
              <Card title={`Serie de probabilidad (%) – ${city}`}>
                <div style={{ width: "100%", height: 380 }}>
                  <ResponsiveContainer>
                    <LineChart data={chartData} margin={{ top: 5, right: 12, left: 0, bottom: 24 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis domain={[0, 100]} />
                      <Tooltip />
                      <ReferenceLine y={20} stroke={colors.ok} strokeDasharray="4 4" />
                      <ReferenceLine y={50} stroke={colors.warn} strokeDasharray="4 4" />
                      <ReferenceLine y={80} stroke={colors.hi} strokeDasharray="4 4" />
                      <Line type="monotone" dataKey="prob" dot={false} stroke="#2563eb" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            )}

            {loading && Loader}
          </>
        )}

        {/* Footer */}
        <div style={{ textAlign: "center", color: "#e2e8f0", marginTop: 18, fontSize: 12 }}>
          © {new Date().getFullYear()} Forest Fire Risk · Tunja — Proyecto académico
        </div>

        {/* Toast */}
        {!!toast && (
          <div
            role="status"
            style={{
              position: "fixed",
              right: 20,
              bottom: 20,
              background: colors.surface,
              border: `1px solid ${colors.outline}`,
              padding: "12px 14px",
              borderRadius: 14,
              boxShadow: "0 12px 40px rgba(2,6,23,.2)",
              fontWeight: 700,
            }}
          >
            {toast}
          </div>
        )}
      </div>
    </div>
  );
}
