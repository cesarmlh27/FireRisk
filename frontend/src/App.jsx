import React, { useEffect, useMemo, useState } from "react";
import {
	Area,
	AreaChart,
	CartesianGrid,
	ReferenceLine,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function riskLevel(p) {
	if (p >= 0.8) return { label: "Muy Alto", cls: "badge--crit", color: "var(--risk-crit)" };
	if (p > 0.5) return { label: "Alto", cls: "badge--hi", color: "var(--risk-hi)" };
	if (p >= 0.2) return { label: "Moderado", cls: "badge--mod", color: "var(--risk-mod)" };
	return { label: "Bajo", cls: "badge--ok", color: "var(--risk-ok)" };
}

const Card = ({ title, accent, right, children }) => (
	<section className={`card ${accent ? `card--${accent}` : ""}`}>
		{(title || right) && (
			<div className="card-header">
				{title && <h3 className="card-title">{title}</h3>}
				{right && <div className="card-actions">{right}</div>}
			</div>
		)}
		{children}
	</section>
);

const KpiCard = ({ label, value, sub, accent }) => (
	<div className={`kpi-card ${accent ? `kpi-card--${accent}` : ""}`}>
		<div className="kpi-label">{label}</div>
		<div className="kpi-value">{value}</div>
		{sub && <div className="kpi-sub">{sub}</div>}
	</div>
);

const Btn = ({ children, variant = "primary", ...props }) => (
	<button className={`btn btn--${variant}`} {...props}>
		{children}
	</button>
);

const RiskBadge = ({ p }) => {
	const meta = riskLevel(p);
	return <span className={`badge ${meta.cls}`}>{meta.label} - {(p * 100).toFixed(1)}%</span>;
};

const Loader = () => (
	<div className="loader">
		<span className="loader-dot" />
		<span className="loader-dot" />
		<span className="loader-dot" />
	</div>
);

const ChartTooltip = ({ active, payload, label }) => {
	if (!active || !payload?.length) return null;
	const val = payload[0]?.value ?? 0;
	const meta = riskLevel(val / 100);
	return (
		<div className="chart-tooltip">
			<div className="chart-tooltip-date">{label}</div>
			<div className="chart-tooltip-row">
				<span style={{ color: meta.color }}>o</span>
				<span className="chart-tooltip-val">{val.toFixed(2)}%</span>
				<span className="chart-tooltip-risk" style={{ color: meta.color }}>
					{meta.label}
				</span>
			</div>
		</div>
	);
};

function RadialGauge({ p }) {
	const pct = Math.max(0, Math.min(100, p * 100));
	const r = 60;
	const c = 2 * Math.PI * r;
	const off = c - (pct / 100) * c;
	const meta = riskLevel(p);

	return (
		<div className="radial-wrap">
			<svg width={170} height={170} viewBox="0 0 170 170">
				<circle cx={85} cy={85} r={r} stroke="rgba(255,255,255,0.08)" strokeWidth={12} fill="none" />
				<circle
					cx={85}
					cy={85}
					r={r}
					stroke={meta.color}
					strokeWidth={12}
					strokeLinecap="round"
					fill="none"
					strokeDasharray={c}
					strokeDashoffset={off}
					transform="rotate(-90 85 85)"
				/>
				<text x={85} y={80} textAnchor="middle" fontSize="28" fontWeight="800" fill="#f4f4f5">
					{pct.toFixed(1)}%
				</text>
				<text x={85} y={98} textAnchor="middle" fontSize="10" fill="#71717a" letterSpacing="1">
					PROB RIESGO
				</text>
			</svg>
		</div>
	);
}

const DataGrid = ({ data }) => {
	if (!data) return null;
	return (
		<div className="data-grid">
			{Object.entries(data)
				.filter(([k]) => k !== "date")
				.map(([k, v]) => (
					<div key={k} className="data-cell">
						<span className="data-key">{k}</span>
						<span className="data-val">{typeof v === "number" ? v.toFixed(3) : String(v)}</span>
					</div>
				))}
		</div>
	);
};

export default function App() {
	const [tab, setTab] = useState("hist");
	const [cities, setCities] = useState(["tunja"]);
	const [city, setCity] = useState("tunja");
	const [days, setDays] = useState([]);
	const [selectedDay, setSelectedDay] = useState("");
	const [loading, setLoading] = useState(false);
	const [result, setResult] = useState(null);
	const [series, setSeries] = useState([]);
	const [range, setRange] = useState({ start: "", end: "" });
	const [apiKey, setApiKey] = useState(sessionStorage.getItem("X_API_KEY") || "");
	const [toast, setToast] = useState("");
	const [error, setError] = useState("");
	const [manual, setManual] = useState({ tmax: "", tmin: "", humidity: "", wind: "", rain_24h: "" });

	const loadLocations = async () => {
		try {
			const r = await fetch(`${API_BASE}/locations`);
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const j = await r.json();
			const all = j.locations?.length ? j.locations : ["tunja"];
			setCities(all);
			setCity((prev) => (all.includes(prev) ? prev : all[0]));
		} catch (e) {
			setError(`No se pudo cargar localidades: ${e.message}`);
		}
	};

	const loadDays = async (targetCity) => {
		if (!targetCity) return;
		try {
			const r = await fetch(`${API_BASE}/days?city=${encodeURIComponent(targetCity)}`);
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const j = await r.json();
			const ds = j.dates || [];
			setDays(ds);
			setSelectedDay(ds[ds.length - 1] || "");
			if (!ds.length) {
				setError(`No hay fechas disponibles para ${targetCity}`);
			}
		} catch (e) {
			setDays([]);
			setSelectedDay("");
			setError(`No se pudo cargar fechas: ${e.message}`);
		}
	};

	useEffect(() => {
		loadLocations();
	}, []);

	useEffect(() => {
		loadDays(city);
	}, [city]);

	const chartData = useMemo(
		() => (series || []).map((p) => ({ date: p.date, prob: +(p.probability * 100).toFixed(3) })),
		[series]
	);

	const stats = useMemo(() => {
		if (!chartData.length) return null;
		const vals = chartData.map((v) => v.prob);
		const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
		return {
			avg: avg.toFixed(1),
			max: Math.max(...vals).toFixed(1),
			crit: vals.filter((v) => v >= 50).length,
			total: vals.length,
		};
	}, [chartData]);

	const fetchByDate = async () => {
		if (!selectedDay) return;
		setLoading(true);
		setError("");
		setResult(null);
		try {
			const r = await fetch(`${API_BASE}/predict/by-date?date=${selectedDay}&city=${encodeURIComponent(city)}`);
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			setResult(await r.json());
		} catch (e) {
			setError(`Error al consultar prediccion: ${e.message}`);
		} finally {
			setLoading(false);
		}
	};

	const fetchManual = async () => {
		setLoading(true);
		setError("");
		setResult(null);
		try {
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
			const r = await fetch(`${API_BASE}/predict`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(body),
			});
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			setResult(await r.json());
		} catch (e) {
			setError(`Error en simulador: ${e.message}`);
		} finally {
			setLoading(false);
		}
	};

	const fetchRange = async () => {
		if (!range.start || !range.end) return;
		setLoading(true);
		setError("");
		setSeries([]);
		try {
			const r = await fetch(
				`${API_BASE}/predict/range?start=${range.start}&end=${range.end}&city=${encodeURIComponent(city)}`
			);
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const j = await r.json();
			setSeries(j.points || []);
		} catch (e) {
			setError(`Error al cargar serie: ${e.message}`);
		} finally {
			setLoading(false);
		}
	};

	const doTrain = async () => {
		const key = apiKey || prompt("API key admin");
		if (!key) return;
		sessionStorage.setItem("X_API_KEY", key);
		setApiKey(key);
		setLoading(true);
		setError("");
		try {
			const r = await fetch(`${API_BASE}/train`, { method: "POST", headers: { "X-API-Key": key } });
			const j = await r.json();
			if (!r.ok) throw new Error(j?.detail || "train error");
			setToast("Modelo reentrenado");
			setTimeout(() => setToast(""), 2500);
		} catch (e) {
			setError(`Error al reentrenar: ${e.message}`);
		} finally {
			setLoading(false);
		}
	};

	return (
		<div className="app-shell">
			<header className="navbar">
				<div className="navbar-inner">
					<div className="logo">
						<div className="logo-icon" aria-hidden>
							<svg width="20" height="20" viewBox="0 0 24 24" fill="none">
								<path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z" fill="#3b82f6" />
							</svg>
						</div>
						<div>
							<span className="logo-name">FireRisk</span>
							<span className="logo-sub">Tunja - ML Analytics</span>
						</div>
					</div>

					<nav className="tab-bar" role="tablist" aria-label="Secciones">
						<button className={`tab${tab === "hist" ? " tab--active" : ""}`} onClick={() => setTab("hist")}>Historico</button>
						<button className={`tab${tab === "manual" ? " tab--active" : ""}`} onClick={() => setTab("manual")}>Simulador</button>
						<button className={`tab${tab === "serie" ? " tab--active" : ""}`} onClick={() => setTab("serie")}>Serie</button>
					</nav>

					<div className="navbar-right">
						<select className="select select--sm" value={city} onChange={(e) => setCity(e.target.value)}>
							{cities.map((c) => (
								<option key={c} value={c}>{c}</option>
							))}
						</select>
						<Btn variant="ghost" onClick={doTrain} disabled={loading}>Reentrenar</Btn>
					</div>
				</div>
			</header>

			<div className="kpi-strip">
				<div className="kpi-strip-inner">
					<KpiCard label="Registros" value={days.length || "-"} sub={city} />
					<KpiCard label="Ultima fecha" value={days[days.length - 1] || "-"} />
					<KpiCard label="Primera fecha" value={days[0] || "-"} />
					{result && <KpiCard label="Ultimo riesgo" value={`${(result.probability * 100).toFixed(1)}%`} sub={riskLevel(result.probability).label} accent="fire" />}
					{stats && <KpiCard label="Promedio" value={`${stats.avg}%`} sub="serie" accent="warn" />}
				</div>
			</div>

			<main className="main-content">
				{tab === "hist" && (
					<div className="tab-content">
						<Card
							title="Consulta historica"
							accent="fire"
							right={<Btn onClick={fetchByDate} disabled={!selectedDay || loading}>{loading ? "Analizando..." : "Analizar"}</Btn>}
						>
							<p className="helper-text">Selecciona una fecha para calcular riesgo con el modelo.</p>
							{!days.length && (
								<div className="field-actions" style={{ marginBottom: 12 }}>
									<Btn variant="ghost" onClick={() => loadDays(city)} disabled={loading}>Reintentar fechas</Btn>
									<Btn variant="ghost" onClick={loadLocations} disabled={loading}>Recargar localidades</Btn>
								</div>
							)}
							<select className="select" style={{ maxWidth: 320 }} value={selectedDay} onChange={(e) => setSelectedDay(e.target.value)}>
								{days.map((d) => (
									<option key={d} value={d}>{d}</option>
								))}
							</select>
						</Card>

						{loading && <Loader />}

						{result && !loading && (
							<div className="result-grid">
								<Card title="Resultado" accent="fire">
									<div className="result-gauge-wrap">
										<RadialGauge p={result.probability || 0} />
										<div className="result-meta">
											<RiskBadge p={result.probability || 0} />
											<div className="result-date">
												<span className="data-key">Fecha</span>
												<span className="data-val mono">{result.analyzed_data?.date}</span>
											</div>
										</div>
									</div>
								</Card>

								<Card title="Variables" accent="cyan">
									<DataGrid data={result.analyzed_data} />
									{result.chart_png_base64 && (
										<img alt="chart" className="prob-img" src={`data:image/png;base64,${result.chart_png_base64}`} />
									)}
								</Card>
							</div>
						)}
					</div>
				)}

				{tab === "manual" && (
					<div className="tab-content">
						<Card title="Simulador" accent="purple">
							<div className="fields-grid">
								{[
									["tmax", "T max (C)"],
									["tmin", "T min (C)"],
									["humidity", "Humedad (%)"],
									["wind", "Viento (km/h)"],
									["rain_24h", "Lluvia 24h (mm)"],
								].map(([k, label]) => (
									<label key={k} className="field">
										<span className="field-label">{label}</span>
										<input
											className="input"
											type="number"
											value={manual[k]}
											onChange={(e) => setManual((prev) => ({ ...prev, [k]: e.target.value }))}
										/>
									</label>
								))}
							</div>
							<div className="field-actions">
								<Btn onClick={fetchManual} disabled={loading}>{loading ? "Calculando..." : "Calcular"}</Btn>
								{result && <RiskBadge p={result.probability || 0} />}
							</div>
						</Card>
					</div>
				)}

				{tab === "serie" && (
					<div className="tab-content">
						<Card
							title="Serie temporal"
							accent="cyan"
							right={<Btn onClick={fetchRange} disabled={loading || !range.start || !range.end}>{loading ? "Calculando..." : "Generar"}</Btn>}
						>
							<div className="date-range-row">
								<label className="field field--inline">
									<span className="field-label">Inicio</span>
									<input className="input" type="date" value={range.start} onChange={(e) => setRange((v) => ({ ...v, start: e.target.value }))} />
								</label>
								<label className="field field--inline">
									<span className="field-label">Fin</span>
									<input className="input" type="date" value={range.end} onChange={(e) => setRange((v) => ({ ...v, end: e.target.value }))} />
								</label>
							</div>
						</Card>

						{!!series.length && (
							<Card title={`Serie de riesgo - ${city}`} accent="cyan">
								<div className="chart-wrap">
									<ResponsiveContainer width="100%" height={380}>
										<AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 34 }}>
											<defs>
												<linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
													<stop offset="5%" stopColor="#22d3ee" stopOpacity={0.22} />
													<stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
												</linearGradient>
											</defs>
											<CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
											<XAxis dataKey="date" tick={{ fill: "#71717a", fontSize: 10 }} tickLine={false} angle={-35} textAnchor="end" dy={8} />
											<YAxis domain={[0, 100]} tick={{ fill: "#71717a", fontSize: 10 }} tickFormatter={(v) => `${v}%`} width={42} />
											<Tooltip content={<ChartTooltip />} />
											<ReferenceLine y={20} stroke="#4ade80" strokeDasharray="4 4" strokeOpacity={0.45} />
											<ReferenceLine y={50} stroke="#fbbf24" strokeDasharray="4 4" strokeOpacity={0.45} />
											<ReferenceLine y={80} stroke="#ef4444" strokeDasharray="4 4" strokeOpacity={0.45} />
											<Area type="monotone" dataKey="prob" stroke="#22d3ee" strokeWidth={2} dot={false} fill="url(#cyanGrad)" />
										</AreaChart>
									</ResponsiveContainer>
								</div>
							</Card>
						)}
					</div>
				)}
			</main>

			<footer className="app-footer">(c) {new Date().getFullYear()} Forest Fire Risk - Tunja</footer>

			{!!toast && <div role="status" className="toast toast--ok">{toast}</div>}
			{!!error && (
				<div role="alert" className="toast toast--err">
					<span>{error}</span>
					<button className="toast-close" onClick={() => setError("")}>x</button>
				</div>
			)}
		</div>
	);
}
