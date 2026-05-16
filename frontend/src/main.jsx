import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  Database,
  FileText,
  Gauge,
  Lock,
  LogOut,
  Mail,
  Network,
  PlayCircle,
  Power,
  RefreshCw,
  Send,
  Server,
  ShieldCheck,
  TerminalSquare,
  UserPlus,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

async function api(path, options = {}) {
  const token = localStorage.getItem("supervision_token");
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Erreur API ${response.status}`);
  }
  return payload;
}

const statusLabel = {
  online: "En ligne",
  degraded: "Degrade",
  offline: "Hors ligne",
  maintenance: "Maintenance",
  running: "Actif",
  stopped: "Arrete",
  unknown: "Inconnu",
  open: "Ouverte",
  acknowledged: "Acquittee",
  resolved: "Resolue",
  pending: "En attente",
  active: "Actif",
  stale: "Silencieux",
  disabled: "Desactive",
  sent: "Envoyee",
  failed: "Echec",
  skipped: "Ignoree",
  approved: "Approuvee",
  success: "Terminee",
};

function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const path = mode === "login" ? "/auth/login/" : "/auth/register/";
      const body = mode === "login"
        ? { username: form.username, password: form.password }
        : form;
      const result = await api(path, { method: "POST", body: JSON.stringify(body) });
      localStorage.setItem("supervision_token", result.token);
      localStorage.setItem("supervision_user", JSON.stringify(result.user));
      onAuth(result.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand">
          <Activity size={30} />
          <div>
            <strong>Supervision IA</strong>
            <span>Monitoring entreprise</span>
          </div>
        </div>
        <div className="auth-tabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
            <Lock size={17} />
            <span>Login</span>
          </button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>
            <UserPlus size={17} />
            <span>Register</span>
          </button>
        </div>
        <form onSubmit={submit}>
          <label>
            Nom utilisateur
            <input
              value={form.username}
              onChange={(event) => setForm({ ...form, username: event.target.value })}
              required
            />
          </label>
          {mode === "register" && (
            <label>
              Email
              <input
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                required
              />
            </label>
          )}
          <label>
            Mot de passe
            <input
              type="password"
              minLength={8}
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              required
            />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-action" disabled={loading}>
            {loading ? "Verification..." : mode === "login" ? "Se connecter" : "Creer le compte"}
          </button>
        </form>
      </section>
    </main>
  );
}

function useMonitoringData(refreshKey, enabled) {
  const [state, setState] = useState({ loading: false, error: "", data: null, refreshedAt: null });

  useEffect(() => {
    if (!enabled) return;
    let alive = true;

    async function load() {
      setState((current) => ({ ...current, loading: true, error: "" }));
      try {
        const [dashboard, servers, alerts, actions, agents, topology, ai] = await Promise.all([
          api("/dashboard/"),
          api("/servers/"),
          api("/alerts/"),
          api("/actions/"),
          api("/agents/"),
          api("/topology/"),
          api("/ai/analysis/"),
        ]);
        if (alive) {
          setState({
            loading: false,
            error: "",
            data: { dashboard, servers, alerts, actions, agents, topology, ai },
            refreshedAt: new Date().toLocaleTimeString(),
          });
        }
      } catch (error) {
        if (alive) setState({ loading: false, error: error.message, data: null, refreshedAt: null });
      }
    }

    load();
    const timer = window.setInterval(load, 5000);

    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [refreshKey, enabled]);

  return state;
}

function StatCard({ icon: Icon, label, value, tone }) {
  return (
    <section className={`stat stat-${tone}`}>
      <div className="stat-icon">
        <Icon size={22} />
      </div>
      <div>
        <p>{label}</p>
        <strong>{value}</strong>
      </div>
    </section>
  );
}

function StatusPill({ value }) {
  return <span className={`pill pill-${value}`}>{statusLabel[value] || value}</span>;
}

function MetricBar({ label, value }) {
  const numeric = Number(value || 0);
  return (
    <div className="metric-bar">
      <div className="metric-label">
        <span>{label}</span>
        <strong>{numeric.toFixed(0)}%</strong>
      </div>
      <div className="track">
        <span style={{ width: `${Math.min(numeric, 100)}%` }} />
      </div>
    </div>
  );
}

function DonutChart({ title, data, colors }) {
  const total = Object.values(data).reduce((sum, value) => sum + value, 0) || 1;
  let offset = 25;
  const segments = Object.entries(data).map(([key, value], index) => {
    const dash = (value / total) * 100;
    const segment = (
      <circle
        key={key}
        cx="72"
        cy="72"
        r="46"
        fill="none"
        pathLength="100"
        stroke={colors[index % colors.length]}
        strokeWidth="18"
        strokeDasharray={`${dash} ${100 - dash}`}
        strokeDashoffset={offset}
      />
    );
    offset -= dash;
    return segment;
  });

  return (
    <section className="chart-card">
      <h3>{title}</h3>
      <div className="donut-wrap">
        <svg viewBox="0 0 144 144" role="img">
          <circle cx="72" cy="72" r="46" fill="none" pathLength="100" stroke="#e8edf4" strokeWidth="18" />
          {segments}
        </svg>
        <strong>{total}</strong>
      </div>
      <div className="legend">
        {Object.entries(data).map(([key, value], index) => (
          <span key={key}>
            <i style={{ background: colors[index % colors.length] }} />
            {statusLabel[key] || key}: {value}
          </span>
        ))}
      </div>
    </section>
  );
}

function BarChart({ title, metrics }) {
  const items = metrics.map((metric) => ({
    name: metric.server,
    cpu: Number(metric.cpu_usage),
    memory: Number(metric.memory_usage),
    disk: Number(metric.disk_usage),
  }));

  return (
    <section className="chart-card chart-wide">
      <h3>{title}</h3>
      <div className="bar-chart">
        {items.map((item) => (
          <div className="bar-group" key={item.name}>
            <span>{item.name}</span>
            <div title={`CPU ${item.cpu}%`} style={{ height: `${item.cpu}%`, background: "#2563eb" }} />
            <div title={`RAM ${item.memory}%`} style={{ height: `${item.memory}%`, background: "#16a34a" }} />
            <div title={`Disque ${item.disk}%`} style={{ height: `${item.disk}%`, background: "#f97316" }} />
          </div>
        ))}
      </div>
      <div className="legend inline">
        <span><i style={{ background: "#2563eb" }} />CPU</span>
        <span><i style={{ background: "#16a34a" }} />RAM</span>
        <span><i style={{ background: "#f97316" }} />Disque</span>
      </div>
    </section>
  );
}

function Dashboard({ data }) {
  const { dashboard, servers, alerts, actions, agents, ai } = data;
  const latestServers = servers.slice(0, 4);
  const metricsWithNames = dashboard.latest_metrics.map((metric) => ({
    ...metric,
    server: servers.find((server) => server.id === metric.server)?.hostname || `srv-${metric.server}`,
  }));

  return (
    <>
      <div className="stats-grid">
        <StatCard icon={Server} label="Serveurs" value={dashboard.servers_total} tone="blue" />
        <StatCard icon={Activity} label="Services" value={dashboard.services_total} tone="green" />
        <StatCard icon={AlertTriangle} label="Alertes ouvertes" value={dashboard.open_alerts} tone="orange" />
        <StatCard icon={Bot} label="Agents actifs" value={`${dashboard.active_agents}/${dashboard.agents_total}`} tone="violet" />
      </div>

      <div className="chart-grid">
        <DonutChart title="Serveurs par statut" data={dashboard.servers_by_status} colors={["#16a34a", "#f97316", "#dc2626", "#6366f1"]} />
        <DonutChart title="Services par statut" data={dashboard.services_by_status} colors={["#0ea5e9", "#f97316", "#dc2626", "#64748b"]} />
        <BarChart title="Utilisation ressources" metrics={metricsWithNames} />
      </div>

      <div className="content-grid">
        <section className="panel wide">
          <div className="panel-head">
            <div>
              <h2>Etat de l'infrastructure</h2>
              <p>Vue consolidee des noeuds critiques et de leurs dernieres metriques.</p>
            </div>
            <Gauge size={22} />
          </div>
          <div className="server-list">
            {latestServers.map((server) => (
              <article className="server-row" key={server.id}>
                <div>
                  <h3>{server.hostname}</h3>
                  <p>{server.ip_address} - {server.location}</p>
                </div>
                <StatusPill value={server.status} />
                <div className="server-metrics">
                  <MetricBar label="CPU" value={server.latest_metric?.cpu_usage} />
                  <MetricBar label="RAM" value={server.latest_metric?.memory_usage} />
                  <MetricBar label="Disque" value={server.latest_metric?.disk_usage} />
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Agents IA</h2>
              <p>Analyse operationnelle et recommandations.</p>
            </div>
            <ShieldCheck size={22} />
          </div>
          <div className="finding-list">
            {ai.findings.map((finding) => (
              <article className="finding" key={finding.agent}>
                <span className={`priority priority-${finding.priority}`}>{finding.priority}</span>
                <h3>{finding.title}</h3>
                <p>{finding.recommendation}</p>
                <small>{finding.agent}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Alertes recentes</h2>
              <p>Incidents a traiter par l'equipe NOC.</p>
            </div>
            <AlertTriangle size={22} />
          </div>
          <div className="compact-list">
            {alerts.slice(0, 5).map((alert) => (
              <article key={alert.id}>
                <strong>{alert.title}</strong>
                <span>{alert.server_name} - {alert.service_name || "serveur"}</span>
                <StatusPill value={alert.status} />
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Administration</h2>
              <p>Actions controlees ou recommandees.</p>
            </div>
            <TerminalSquare size={22} />
          </div>
          <div className="compact-list">
            {actions.map((action) => (
              <article key={action.id}>
                <strong>{action.action_type.replaceAll("_", " ")}</strong>
                <span>{action.target_server_name} - {action.notes}</span>
                <StatusPill value={action.status} />
              </article>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>Collecte et alerting</h2>
              <p>Agents deployes et derniers envois email.</p>
            </div>
            <Mail size={22} />
          </div>
          <div className="compact-list">
            {agents.slice(0, 3).map((agent) => (
              <article key={agent.id}>
                <strong>{agent.name}</strong>
                <span>{agent.server_name} - v{agent.version}</span>
                <StatusPill value={agent.status} />
              </article>
            ))}
            {dashboard.latest_notifications.slice(0, 2).map((notification) => (
              <article key={`notification-${notification.id}`}>
                <strong>{notification.alert_title}</strong>
                <span>{notification.recipient}</span>
                <StatusPill value={notification.status} />
              </article>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}

function Infrastructure({ servers, onReboot }) {
  return (
    <section className="panel wide">
      <div className="panel-head">
        <div>
          <h2>Inventaire serveurs et services</h2>
          <p>Cartographie logique des composants surveilles.</p>
        </div>
        <Database size={22} />
      </div>
      <div className="inventory-grid">
        {servers.map((server) => (
          <article className="inventory-card" key={server.id}>
            <div className="inventory-card-head">
              <div>
                <h3>{server.hostname}</h3>
                <p>{server.os_family} - {server.environment}</p>
              </div>
              <div className="inventory-actions">
                <StatusPill value={server.status} />
                <button className="small-action danger-action" onClick={() => onReboot(server)}>
                  <Power size={16} />
                  <span>Redemarrer</span>
                </button>
              </div>
            </div>
            <div className="service-stack">
              {server.services.map((service) => (
                <div className="service-line" key={service.id}>
                  <span>{service.name}</span>
                  <small>{service.protocol}/{service.port || "-"}</small>
                  <StatusPill value={service.status} />
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function Alerts({ alerts }) {
  return (
    <section className="panel wide">
      <div className="panel-head">
        <div>
          <h2>Centre d'alertes</h2>
          <p>Qualification, criticite et etat de traitement.</p>
        </div>
        <AlertTriangle size={22} />
      </div>
      <table>
        <thead>
          <tr>
            <th>Alerte</th>
            <th>Cible</th>
            <th>Severite</th>
            <th>Statut</th>
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert) => (
            <tr key={alert.id}>
              <td>
                <strong>{alert.title}</strong>
                <span>{alert.description}</span>
              </td>
              <td>{alert.server_name}</td>
              <td><span className={`severity severity-${alert.severity}`}>{alert.severity}</span></td>
              <td><StatusPill value={alert.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Topology({ topology }) {
  const servicesByServer = topology.nodes
    .filter((node) => node.type === "service")
    .reduce((groups, service) => {
      groups[service.server] = [...(groups[service.server] || []), service];
      return groups;
    }, {});
  const servers = topology.nodes.filter((node) => node.type === "server");

  return (
    <section className="panel wide">
      <div className="panel-head">
        <div>
          <h2>Topologie reseau</h2>
          <p>Relations entre serveurs supervises, agents et services metier.</p>
        </div>
        <Network size={22} />
      </div>
      <div className="topology-map">
        {servers.map((server) => {
          const serverId = Number(server.id.replace("server-", ""));
          return (
            <article className={`topology-node topology-${server.status}`} key={server.id}>
              <div className="node-server">
                <Server size={20} />
                <div>
                  <strong>{server.label}</strong>
                  <StatusPill value={server.status} />
                </div>
              </div>
              <div className="node-links">
                {(servicesByServer[serverId] || []).map((service) => (
                  <span className={`node-service node-service-${service.status}`} key={service.id}>
                    {service.label}
                  </span>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function Agents({ ai }) {
  return (
    <section className="panel wide">
      <div className="panel-head">
        <div>
          <h2>Console des agents IA</h2>
          <p>{ai.summary}</p>
        </div>
        <Bot size={22} />
      </div>
      <div className="agent-console">
        <div className="score-ring">
          <strong>{ai.health_score}</strong>
          <span>score global</span>
        </div>
        <div className="finding-list">
          {ai.findings.map((finding) => (
            <article className="finding" key={finding.agent}>
              <span className={`priority priority-${finding.priority}`}>{finding.priority}</span>
              <h3>{finding.agent}</h3>
              <p>{finding.title}</p>
              <small>{finding.recommendation}</small>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function AdminActions({ actions, onExecute }) {
  return (
    <section className="panel wide">
      <div className="panel-head">
        <div>
          <h2>Administration controlee</h2>
          <p>Operations preparees avec validation humaine.</p>
        </div>
        <PlayCircle size={22} />
      </div>
      <div className="action-grid">
        {actions.map((action) => (
          <article className="action-card" key={action.id}>
            <CheckCircle2 size={20} />
            <h3>{action.action_type.replaceAll("_", " ")}</h3>
            <p>{action.target_server_name} - {action.target_service_name || "serveur"}</p>
            <small>{action.notes}</small>
            <StatusPill value={action.status} />
            {["pending", "approved", "failed"].includes(action.status) && (
              <button className="small-action" onClick={() => onExecute(action.id)}>
                <PlayCircle size={16} />
                <span>Executer</span>
              </button>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function App() {
  const savedUser = localStorage.getItem("supervision_user");
  const [user, setUser] = useState(savedUser ? JSON.parse(savedUser) : null);
  const [view, setView] = useState("dashboard");
  const [refreshKey, setRefreshKey] = useState(0);
  const [operation, setOperation] = useState("");
  const { loading, error, data, refreshedAt } = useMonitoringData(refreshKey, Boolean(user));

  const navItems = useMemo(
    () => [
      ["dashboard", "Dashboard", Gauge],
      ["infra", "Infrastructure", Server],
      ["topology", "Topologie", Network],
      ["alerts", "Alertes", AlertTriangle],
      ["agents", "Agents IA", Bot],
      ["admin", "Admin", TerminalSquare],
    ],
    []
  );

  async function handleLogout() {
    await api("/auth/logout/", { method: "POST" }).catch(() => null);
    localStorage.removeItem("supervision_token");
    localStorage.removeItem("supervision_user");
    setUser(null);
  }

  async function runMonitoringCycle() {
    setOperation("Simulation en cours...");
    try {
      const result = await api("/monitoring/simulate/", { method: "POST" });
      setOperation(`${result.detail} ${result.metrics} metrique(s), ${result.alerts} alerte(s).`);
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setOperation(err.message);
    }
  }

  async function executeAction(actionId) {
    setOperation("Execution de l'action...");
    try {
      await api(`/actions/${actionId}/execute/`, { method: "POST" });
      setOperation("Action executee.");
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setOperation(err.message);
    }
  }

  async function downloadReport() {
    setOperation("Generation du rapport PDF...");
    try {
      const token = localStorage.getItem("supervision_token");
      const response = await fetch(`${API_BASE}/reports/pdf/`, {
        headers: token ? { Authorization: `Token ${token}` } : {},
      });
      if (!response.ok) {
        throw new Error(`Erreur rapport PDF ${response.status}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `rapport-supervision-${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setOperation("Rapport PDF genere.");
    } catch (err) {
      setOperation(err.message);
    }
  }

  async function rebootServer(server) {
    const confirmed = window.confirm(`Redemarrer ${server.hostname} (${server.ip_address}) ?`);
    if (!confirmed) return;

    setOperation(`Demande de redemarrage envoyee pour ${server.hostname}...`);
    try {
      await api(`/servers/${server.id}/reboot/`, { method: "POST" });
      setOperation("Commande creee. L'agent l'executera au prochain heartbeat si ALLOW_REMOTE_REBOOT=true.");
      setRefreshKey((key) => key + 1);
    } catch (err) {
      setOperation(err.message);
    }
  }

  if (!user) {
    return <AuthScreen onAuth={setUser} />;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Activity size={28} />
          <div>
            <strong>Supervision IA</strong>
            <span>NOC Enterprise</span>
          </div>
        </div>
        <nav>
          {navItems.map(([key, label, Icon]) => (
            <button className={view === key ? "active" : ""} key={key} onClick={() => setView(key)}>
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <button className="logout-button" onClick={handleLogout}>
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h1>Supervision, monitoring et administration</h1>
            <p>Connecte: {user.username}</p>
          </div>
          <button className="refresh" onClick={() => setRefreshKey((key) => key + 1)}>
            <RefreshCw size={18} />
            <span>Actualiser</span>
          </button>
          <button className="refresh" onClick={downloadReport}>
            <FileText size={18} />
            <span>Rapport PDF</span>
          </button>
          <button className="refresh primary-refresh" onClick={runMonitoringCycle}>
            <Send size={18} />
            <span>Simuler cycle</span>
          </button>
          {refreshedAt && <div className="refresh-state">Mis a jour a {refreshedAt}</div>}
        </header>

        {operation && <div className="operation-banner">{operation}</div>}
        {loading && <div className="empty-state">Chargement des donnees de supervision...</div>}
        {error && <div className="empty-state error">Backend indisponible: {error}</div>}
        {data && view === "dashboard" && <Dashboard data={data} />}
        {data && view === "infra" && <Infrastructure servers={data.servers} onReboot={rebootServer} />}
        {data && view === "topology" && <Topology topology={data.topology} />}
        {data && view === "alerts" && <Alerts alerts={data.alerts} />}
        {data && view === "agents" && <Agents ai={data.ai} />}
        {data && view === "admin" && <AdminActions actions={data.actions} onExecute={executeAction} />}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
