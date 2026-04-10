import { useState, useRef } from "react"
import axios from "axios"

const API = "http://localhost:8000"

export default function App() {
  const [topic, setTopic] = useState("")
  const [steps, setSteps] = useState([])
  const [finalStats, setFinalStats] = useState(null)
  const [summary, setSummary] = useState("")
  const [running, setRunning] = useState(false)
  const [error, setError] = useState("")
  const eventSource = useRef(null)

  const startResearch = async () => {
    if (!topic.trim()) return
    setSteps([])
    setFinalStats(null)
    setSummary("")
    setError("")
    setRunning(true)

    try {
      const res = await axios.post(`${API}/research`, { topic })
      setSteps(res.data.steps)
      setFinalStats(res.data.final_stats)
      setSummary(res.data.summary)
    } catch (e) {
      setError("Backend error — is the server running?")
    } finally {
      setRunning(false)
    }
  }

  const usagePct = finalStats?.usage_pct ?? 0
  const usageColor = usagePct > 80 ? "#ef4444" : usagePct > 50 ? "#f59e0b" : "#22c55e"

  return (
    <div style={styles.app}>
      <div style={styles.header}>
        <h1 style={styles.title}>⚡ ContextPilot</h1>
        <p style={styles.subtitle}>Agentic research with live context management</p>
      </div>

      <div style={styles.inputRow}>
        <input
          style={styles.input}
          placeholder="Enter a research topic..."
          value={topic}
          onChange={e => setTopic(e.target.value)}
          onKeyDown={e => e.key === "Enter" && startResearch()}
          disabled={running}
        />
        <button style={styles.button} onClick={startResearch} disabled={running}>
          {running ? "Researching..." : "Research"}
        </button>
      </div>

      {error && <p style={styles.error}>{error}</p>}

      {running && (
        <div style={styles.card}>
          <p style={{ color: "#94a3b8" }}>🔍 Agent is running... this takes ~15 seconds</p>
        </div>
      )}

      {finalStats && (
        <div style={styles.statsRow}>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Context Usage</div>
            <div style={{ ...styles.statValue, color: usageColor }}>{usagePct}%</div>
            <div style={styles.progressBar}>
              <div style={{ ...styles.progressFill, width: `${usagePct}%`, background: usageColor }} />
            </div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Tokens Evicted</div>
            <div style={styles.statValue}>{finalStats.total_evicted}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Chunks in Context</div>
            <div style={styles.statValue}>{finalStats.chunk_count}</div>
          </div>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Evictions</div>
            <div style={styles.statValue}>{finalStats.eviction_log.length}</div>
          </div>
        </div>
      )}

      {steps.length > 0 && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Agent Steps</h2>
          {steps.map((s, i) => (
            <div key={i} style={styles.stepCard}>
              <div style={styles.stepHeader}>
                <span style={styles.stepNum}>Step {s.step}</span>
                <span style={styles.stepMeta}>⏱ {s.ttft_ms}ms · 🧩 {s.chunks_in_context} chunks · 📊 {s.context_usage_pct}% full</span>
              </div>
              <div style={styles.question}>Q: {s.question}</div>
              <div style={styles.answer}>A: {s.answer}</div>
            </div>
          ))}
        </div>
      )}

      {summary && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Summary</h2>
          <div style={styles.card}><p style={{ color: "#e2e8f0", lineHeight: 1.7 }}>{summary}</p></div>
        </div>
      )}

      {finalStats?.eviction_log?.length > 0 && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Eviction Log</h2>
          {finalStats.eviction_log.map((e, i) => (
            <div key={i} style={styles.evictionCard}>
              <span style={styles.evictedTag}>EVICTED</span>
              <span style={{ color: "#94a3b8", fontSize: 13 }}>{e.preview}</span>
              <span style={{ color: "#64748b", fontSize: 12, marginLeft: "auto" }}>score: {e.score} · {e.tokens} tokens</span>
            </div>
          ))}
        </div>
      )}

      {finalStats?.chunks?.length > 0 && (
        <div style={styles.section}>
          <h2 style={styles.sectionTitle}>Context Buffer (surviving chunks)</h2>
          {finalStats.chunks.map((c, i) => (
            <div key={i} style={styles.chunkCard}>
              <span style={{ ...styles.roleTag, background: c.role === "user" ? "#1d4ed8" : "#065f46" }}>{c.role}</span>
              <span style={{ color: "#cbd5e1", fontSize: 13 }}>{c.preview}</span>
              <span style={{ color: "#64748b", fontSize: 12, marginLeft: "auto" }}>score: {c.score}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const styles = {
  app: { maxWidth: 860, margin: "0 auto", padding: "40px 24px", fontFamily: "'IBM Plex Mono', monospace", background: "#0f172a", minHeight: "100vh", color: "#e2e8f0" },
  header: { marginBottom: 32 },
  title: { fontSize: 32, fontWeight: 700, color: "#f8fafc", margin: 0 },
  subtitle: { color: "#64748b", marginTop: 6, fontSize: 14 },
  inputRow: { display: "flex", gap: 12, marginBottom: 24 },
  input: { flex: 1, padding: "12px 16px", borderRadius: 8, border: "1px solid #1e293b", background: "#1e293b", color: "#f8fafc", fontSize: 15, outline: "none" },
  button: { padding: "12px 24px", borderRadius: 8, border: "none", background: "#3b82f6", color: "#fff", fontWeight: 600, cursor: "pointer", fontSize: 15 },
  error: { color: "#ef4444", fontSize: 14 },
  card: { background: "#1e293b", borderRadius: 10, padding: "16px 20px", marginBottom: 12 },
  statsRow: { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 28 },
  statCard: { background: "#1e293b", borderRadius: 10, padding: "16px 20px" },
  statLabel: { color: "#64748b", fontSize: 12, marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 },
  statValue: { fontSize: 28, fontWeight: 700, color: "#f8fafc" },
  progressBar: { height: 4, background: "#0f172a", borderRadius: 2, marginTop: 8 },
  progressFill: { height: "100%", borderRadius: 2, transition: "width 0.3s" },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 16, fontWeight: 600, color: "#94a3b8", marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 },
  stepCard: { background: "#1e293b", borderRadius: 10, padding: "16px 20px", marginBottom: 10 },
  stepHeader: { display: "flex", justifyContent: "space-between", marginBottom: 10 },
  stepNum: { color: "#3b82f6", fontWeight: 600, fontSize: 13 },
  stepMeta: { color: "#475569", fontSize: 12 },
  question: { color: "#94a3b8", fontSize: 13, marginBottom: 8 },
  answer: { color: "#e2e8f0", fontSize: 14, lineHeight: 1.6 },
  evictionCard: { display: "flex", alignItems: "center", gap: 12, background: "#1e293b", borderRadius: 8, padding: "10px 16px", marginBottom: 8 },
  evictedTag: { background: "#7f1d1d", color: "#fca5a5", fontSize: 11, padding: "2px 8px", borderRadius: 4, fontWeight: 600, whiteSpace: "nowrap" },
  chunkCard: { display: "flex", alignItems: "center", gap: 12, background: "#1e293b", borderRadius: 8, padding: "10px 16px", marginBottom: 8 },
  roleTag: { color: "#fff", fontSize: 11, padding: "2px 8px", borderRadius: 4, fontWeight: 600, whiteSpace: "nowrap" },
}