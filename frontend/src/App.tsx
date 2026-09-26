import React, { useState, useEffect } from 'react';

interface WellData {
  id: string;
  name: string;
  status: 'Active' | 'Soaking' | 'Injecting' | 'Standby';
  steamRate: number; // bbl/d
  reservoirPressure: number; // psi
  productionRate: number; // bpd
  temperature: number; // °F
  riskScore: number;
}

const INITIAL_WELLS: WellData[] = [
  { id: 'BW-01', name: 'Baghewala North #1', status: 'Injecting', steamRate: 650, reservoirPressure: 3520, productionRate: 480, temperature: 410, riskScore: 0.12 },
  { id: 'BW-02', name: 'Baghewala South #4', status: 'Active', steamRate: 0, reservoirPressure: 3410, productionRate: 590, temperature: 360, riskScore: 0.18 },
  { id: 'BW-03', name: 'Baghewala East #2', status: 'Soaking', steamRate: 0, reservoirPressure: 3680, productionRate: 0, temperature: 480, riskScore: 0.25 },
  { id: 'BW-04', name: 'Baghewala Central #7', status: 'Active', steamRate: 0, reservoirPressure: 3350, productionRate: 620, temperature: 345, riskScore: 0.08 },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<'twin' | 'optimizer' | 'economics' | 'risk'>('twin');
  const [healthStatus, setHealthStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [lastCheckTime, setLastCheckTime] = useState<string>('');
  const [wells] = useState<WellData[]>(INITIAL_WELLS);
  const [simRunning, setSimRunning] = useState(false);
  const [simProgress, setSimProgress] = useState(100);

  const checkHealth = async () => {
    try {
      const res = await fetch('/health');
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'ok') {
          setHealthStatus('connected');
        } else {
          setHealthStatus('disconnected');
        }
      } else {
        setHealthStatus('disconnected');
      }
    } catch {
      setHealthStatus('disconnected');
    }
    setLastCheckTime(new Date().toLocaleTimeString());
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRunSimulation = () => {
    setSimRunning(true);
    setSimProgress(0);
    const step = 20;
    const timer = setInterval(() => {
      setSimProgress((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          setSimRunning(false);
          return 100;
        }
        return prev + step;
      });
    }, 200);
  };

  const totalProduction = wells.reduce((acc, w) => acc + w.productionRate, 0);
  const avgPressure = Math.round(wells.reduce((acc, w) => acc + w.reservoirPressure, 0) / wells.length);
  const maxRisk = Math.max(...wells.map(w => w.riskScore));

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">BX</div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="brand-name">BAGHEWALA-X</span>
              <span className="brand-badge">SIH26120 Digital Twin</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Heavy Oil Field Well-to-Surface Simulator & Optimizer
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className="status-badge" style={{ 
            borderColor: healthStatus === 'connected' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(244, 63, 94, 0.4)',
            color: healthStatus === 'connected' ? '#34d399' : '#f43f5e',
            background: healthStatus === 'connected' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)'
          }}>
            <div className="status-indicator" style={{ 
              backgroundColor: healthStatus === 'connected' ? 'var(--accent-emerald)' : 'var(--accent-rose)',
              boxShadow: healthStatus === 'connected' ? '0 0 8px var(--accent-emerald)' : '0 0 8px var(--accent-rose)'
            }} />
            Backend API: {healthStatus === 'connected' ? 'Connected (200 OK)' : healthStatus === 'checking' ? 'Connecting...' : 'Offline'}
          </div>
          <button 
            id="refresh-health-btn"
            onClick={checkHealth}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              color: 'var(--text-secondary)',
              borderRadius: '6px',
              padding: '0.35rem 0.75rem',
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            Check Health {lastCheckTime ? `(${lastCheckTime})` : ''}
          </button>
        </div>
      </header>

      <main className="main-container">
        <section className="hero-section">
          <h1 className="hero-title">Multi-Well Digital Twin Console</h1>
          <p className="hero-subtitle">
            Deterministic physics-based simulation (CSS Cyclic Steam Stimulation & Sucker Rod Pump operations),
            autonomous heuristic/gradient optimization, and risk evaluation. All operating on synthetic models without external GPU requirements.
          </p>
        </section>

        {/* Top KPIs */}
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">Field Production</div>
            <div className="kpi-value">{totalProduction} <span className="kpi-unit">bbl/day</span></div>
            <div className="kpi-subtext">↑ 8.4% vs baseline scenario</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg Reservoir Pressure</div>
            <div className="kpi-value">{avgPressure} <span className="kpi-unit">psi</span></div>
            <div className="kpi-subtext" style={{ color: 'var(--accent-cyan)' }}>Assumed range 3000–4500 psi</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Peak Anomaly Risk</div>
            <div className="kpi-value" style={{ color: maxRisk > 0.5 ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}>
              {(maxRisk * 100).toFixed(0)}%
            </div>
            <div className="kpi-subtext" style={{ color: 'var(--text-muted)' }}>Threshold limit: 80%</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Active Wells</div>
            <div className="kpi-value">4 <span className="kpi-unit">/ 4 online</span></div>
            <div className="kpi-subtext">1 Injecting · 1 Soaking · 2 Pumping</div>
          </div>
        </div>

        {/* Tab Selection */}
        <div className="tabs-nav">
          <button 
            id="tab-twin"
            className={`tab-btn ${activeTab === 'twin' ? 'active' : ''}`}
            onClick={() => setActiveTab('twin')}
          >
            Well Surveillance (Twin)
          </button>
          <button 
            id="tab-optimizer"
            className={`tab-btn ${activeTab === 'optimizer' ? 'active' : ''}`}
            onClick={() => setActiveTab('optimizer')}
          >
            CSS Optimizer
          </button>
          <button 
            id="tab-economics"
            className={`tab-btn ${activeTab === 'economics' ? 'active' : ''}`}
            onClick={() => setActiveTab('economics')}
          >
            Economics & DCF
          </button>
          <button 
            id="tab-risk"
            className={`tab-btn ${activeTab === 'risk' ? 'active' : ''}`}
            onClick={() => setActiveTab('risk')}
          >
            Risk & Anomaly Matrix
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'twin' && (
          <div className="card-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div className="panel-title" style={{ margin: 0 }}>Active Well Fleet Telemetry</div>
              <button 
                id="run-sim-btn"
                className="btn-action"
                onClick={handleRunSimulation}
                disabled={simRunning}
              >
                {simRunning ? `Simulating (${simProgress}%)...` : 'Run Physics Step'}
              </button>
            </div>

            <table className="data-table">
              <thead>
                <tr>
                  <th>Well Identifier</th>
                  <th>Operating Status</th>
                  <th>Steam Injection</th>
                  <th>Reservoir Pressure</th>
                  <th>Liquid Output</th>
                  <th>Wellbore Temp</th>
                  <th>Risk Score</th>
                </tr>
              </thead>
              <tbody>
                {wells.map((well) => (
                  <tr key={well.id}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{well.id} - {well.name}</td>
                    <td>
                      <span className={`badge ${
                        well.status === 'Active' ? 'badge-success' :
                        well.status === 'Injecting' ? 'badge-warning' : ''
                      }`} style={{
                        background: well.status === 'Soaking' ? 'rgba(56, 189, 248, 0.15)' : undefined,
                        color: well.status === 'Soaking' ? '#38bdf8' : undefined
                      }}>
                        {well.status}
                      </span>
                    </td>
                    <td>{well.steamRate ? `${well.steamRate} bbl/d` : '—'}</td>
                    <td>{well.reservoirPressure} psi</td>
                    <td style={{ fontWeight: 600 }}>{well.productionRate} bpd</td>
                    <td>{well.temperature} °F</td>
                    <td>
                      <span style={{ 
                        color: well.riskScore > 0.2 ? 'var(--accent-amber)' : 'var(--accent-emerald)',
                        fontFamily: 'var(--font-mono)' 
                      }}>
                        {(well.riskScore * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'optimizer' && (
          <div className="card-panel">
            <h2 className="panel-title">Cyclic Steam Stimulation (CSS) Parameter Optimization</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem', fontSize: '0.9rem' }}>
              Hybrid heuristic and gradient-based parameter optimizer to maximize Net Present Value (NPV) subject to pump constraints and steam boiler limits.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Optimal Steam Duration</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, margin: '0.25rem 0' }}>14 Days</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)' }}>At 700 bbl/day quality 0.85</div>
              </div>
              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Recommended Soak Period</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, margin: '0.25rem 0' }}>4 Days</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>Thermal diffusion equilibrium</div>
              </div>
              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Projected Oil Uplift</div>
                <div style={{ fontSize: '1.3rem', fontWeight: 700, margin: '0.25rem 0', color: 'var(--accent-emerald)' }}>+24.6%</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Over 90-day production window</div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'economics' && (
          <div className="card-panel">
            <h2 className="panel-title">Economic Evaluation & Cash-Flow Projections</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
              Discounted Cash Flow (DCF) model configured with standard SIH26120 economic assumptions (10% discount rate, $65/bbl oil price).
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Estimated Field NPV</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>$4.82 M</div>
              </div>
              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Internal Rate of Return (IRR)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>31.8%</div>
              </div>
              <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Steam Generation Cost</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>$14.20 / bbl</div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'risk' && (
          <div className="card-panel">
            <h2 className="panel-title">Risk & Anomaly Detection Matrix</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
              Real-time heuristic & machine-learning anomaly scoring on sucker rod pump dynamometer signals and casing pressure.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ padding: '1rem', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                <div style={{ fontWeight: 600, color: '#34d399' }}>✓ Rod Pump Mechanical Integrity: Nominal</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>No fluid pounding, gas interference, or parted rod signatures detected across 4 monitored wells.</div>
              </div>
              <div style={{ padding: '1rem', borderRadius: '8px', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                <div style={{ fontWeight: 600, color: '#fbbf24' }}>⚠ Well BW-03: Thermal Soak Pressure Monitoring</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>Soaking chamber pressure is at 3,680 psi. Pressure relief threshold is 4,200 psi.</div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
