import { useState, useEffect, useCallback } from "react";

const API = "http://localhost:8000";

const STATUS = {
  ACCEPT: { bg: "#EAF3DE", color: "#27500A", border: "#97C459", dot: "#639922", label: "Accepted" },
  FLAG:   { bg: "#FAEEDA", color: "#633806", border: "#EF9F27", dot: "#BA7517", label: "Flagged"  },
  REJECT: { bg: "#FCEBEB", color: "#791F1F", border: "#F09595", dot: "#E24B4A", label: "Rejected" },
};

const fmt = (n) => n != null ? `$${Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—";

function Badge({ status }) {
  const s = STATUS[status];
  if (!s) return null;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      background: s.bg, color: s.color,
      border: `1px solid ${s.border}`,
      borderRadius: 20, padding: "3px 10px 3px 8px",
      fontSize: 12, fontWeight: 500, whiteSpace: "nowrap",
    }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: s.dot, flexShrink: 0 }} />
      {s.label}
    </span>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <div style={{
      flex: 1, minWidth: 0,
      background: "#fff",
      border: "1px solid #e8e6e0",
      borderTop: accent ? `3px solid ${accent}` : "1px solid #e8e6e0",
      borderRadius: 12,
      padding: "1.1rem 1.25rem",
    }}>
      <p style={{ margin: 0, fontSize: 12, color: "#888780", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 500 }}>{label}</p>
      <p style={{ margin: "6px 0 0", fontSize: 32, fontWeight: 500, color: "#2C2C2A", lineHeight: 1 }}>{value}</p>
    </div>
  );
}

function Sidebar({ summary, filter, setFilter, onUpload, uploading }) {
  const [dragging, setDragging] = useState(false);

  const handleFile = (file) => {
    if (!file?.name.endsWith(".pdf")) return alert("Please upload a PDF.");
    onUpload(file);
  };

  const navItems = [
    { key: "ALL",    label: "All claims",   count: summary.total  },
    { key: "ACCEPT", label: "Accepted",     count: summary.ACCEPT },
    { key: "FLAG",   label: "Flagged",      count: summary.FLAG   },
    { key: "REJECT", label: "Rejected",     count: summary.REJECT },
  ];

  const dotColors = { ALL: "#888780", ACCEPT: "#639922", FLAG: "#BA7517", REJECT: "#E24B4A" };

  return (
    <aside style={{
      width: 220, flexShrink: 0,
      display: "flex", flexDirection: "column", gap: 0,
      borderRight: "1px solid #e8e6e0",
      background: "#faf9f7",
      padding: "1.5rem 0",
      height: "100vh",
      position: "sticky",
      top: 0,
      overflowY: "auto",
    }}>
      <div style={{ padding: "0 1.25rem 1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: "#2C2C2A",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <rect x="1" y="1" width="5" height="5" rx="1" fill="#fff" opacity="0.9"/>
              <rect x="8" y="1" width="5" height="5" rx="1" fill="#fff" opacity="0.6"/>
              <rect x="1" y="8" width="5" height="5" rx="1" fill="#fff" opacity="0.6"/>
              <rect x="8" y="8" width="5" height="5" rx="1" fill="#fff" opacity="0.9"/>
            </svg>
          </div>
          <span style={{ fontWeight: 500, fontSize: 14, color: "#2C2C2A" }}>ClaimIQ</span>
        </div>
      </div>

      <nav style={{ padding: "0 0.75rem", marginBottom: "1.5rem" }}>
        <p style={{ fontSize: 11, fontWeight: 500, color: "#B4B2A9", textTransform: "uppercase", letterSpacing: "0.07em", padding: "0 0.5rem", marginBottom: 4 }}>Queue</p>
        {navItems.map(({ key, label, count }) => (
          <button key={key} onClick={() => setFilter(key)} style={{
            width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "7px 10px", borderRadius: 8, border: "none", cursor: "pointer",
            background: filter === key ? "#fff" : "transparent",
            boxShadow: filter === key ? "0 1px 3px rgba(0,0,0,0.06), inset 0 0 0 1px #e8e6e0" : "none",
            marginBottom: 2,
          }}>
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: dotColors[key], flexShrink: 0 }} />
              <span style={{ fontSize: 13, color: filter === key ? "#2C2C2A" : "#5F5E5A", fontWeight: filter === key ? 500 : 400 }}>{label}</span>
            </span>
            <span style={{
              fontSize: 11, fontWeight: 500,
              background: filter === key ? "#F1EFE8" : "transparent",
              color: "#888780",
              borderRadius: 10, padding: "1px 7px",
              minWidth: 20, textAlign: "center",
            }}>{count}</span>
          </button>
        ))}
      </nav>

      <div style={{ padding: "0 0.75rem", marginTop: "auto" }}>
        <p style={{ fontSize: 11, fontWeight: 500, color: "#B4B2A9", textTransform: "uppercase", letterSpacing: "0.07em", padding: "0 0.5rem", marginBottom: 8 }}>Upload</p>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
          onClick={() => document.getElementById("file-upload").click()}
          style={{
            border: `1.5px dashed ${dragging ? "#378ADD" : "#D3D1C7"}`,
            borderRadius: 10,
            padding: "1rem 0.75rem",
            textAlign: "center",
            background: dragging ? "#E6F1FB" : "#fff",
            cursor: "pointer",
            transition: "all 0.15s",
          }}
        >
          <input id="file-upload" type="file" accept=".pdf" style={{ display: "none" }} onChange={(e) => handleFile(e.target.files[0])} />
          {uploading ? (
            <>
              <div style={{ width: 20, height: 20, border: "2px solid #D3D1C7", borderTop: "2px solid #5F5E5A", borderRadius: "50%", margin: "0 auto 6px", animation: "spin 0.8s linear infinite" }} />
              <p style={{ margin: 0, fontSize: 12, color: "#888780" }}>Processing...</p>
            </>
          ) : (
            <>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={{ margin: "0 auto 6px", display: "block" }}>
                <path d="M10 13V4M10 4L7 7M10 4L13 7" stroke="#888780" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M3 14v1a2 2 0 002 2h10a2 2 0 002-2v-1" stroke="#888780" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <p style={{ margin: 0, fontSize: 12, color: "#5F5E5A", fontWeight: 500 }}>Drop PDF here</p>
              <p style={{ margin: "2px 0 0", fontSize: 11, color: "#B4B2A9" }}>or click to browse</p>
            </>
          )}
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    </aside>
  );
}

function ClaimRow({ claim, onClick }) {
  const d = claim.extracted_data || {};
  const [hov, setHov] = useState(false);
  return (
    <tr
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{ background: hov ? "#faf9f7" : "#fff", cursor: "pointer", borderBottom: "1px solid #f0eee8" }}
    >
      <td style={{ padding: "11px 16px", maxWidth: 180 }}>
        <span style={{ fontSize: 13, color: "#2C2C2A", fontWeight: 500, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {d.claimant_name || <span style={{ color: "#B4B2A9", fontWeight: 400 }}>Unknown</span>}
        </span>
        <span style={{ fontSize: 11, color: "#B4B2A9", display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginTop: 1 }}>
          {claim.file_name}
        </span>
      </td>
      <td style={{ padding: "11px 16px", fontSize: 12, color: "#888780", fontFamily: "monospace" }}>
        {d.policy_number || <span style={{ color: "#D3D1C7" }}>—</span>}
      </td>
      <td style={{ padding: "11px 16px", fontSize: 13, color: "#2C2C2A" }}>
        {d.claim_amount != null ? fmt(d.claim_amount) : <span style={{ color: "#D3D1C7" }}>—</span>}
      </td>
      <td style={{ padding: "11px 16px", fontSize: 12, color: "#888780" }}>
        {d.incident_date || <span style={{ color: "#D3D1C7" }}>—</span>}
      </td>
      <td style={{ padding: "11px 16px", fontSize: 12, color: "#888780" }}>
        {d.claim_type || <span style={{ color: "#D3D1C7" }}>—</span>}
      </td>
      <td style={{ padding: "11px 16px" }}>
        <Badge status={claim.decision?.status} />
      </td>
      <td style={{ padding: "11px 16px" }}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ opacity: hov ? 0.5 : 0.2, transition: "opacity 0.15s" }}>
          <path d="M5 3l4 4-4 4" stroke="#2C2C2A" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </td>
    </tr>
  );
}

function DetailPanel({ claim, onClose, onDelete }) {
  const d = claim.extracted_data || {};
  const v = claim.validation || {};
  const dec = claim.decision || {};

  const fields = [
    ["Claimant",      d.claimant_name],
    ["Policy number", d.policy_number],
    ["Claim amount",  d.claim_amount != null ? fmt(d.claim_amount) : null],
    ["Incident date", d.incident_date],
    ["Claim type",    d.claim_type],
  ];

  return (
    <div style={{
      width: 380, flexShrink: 0,
      borderLeft: "1px solid #e8e6e0",
      background: "#fff",
      display: "flex", flexDirection: "column",
      minHeight: "100vh",
    }}>
      <div style={{
        padding: "1.25rem 1.25rem 1rem",
        borderBottom: "1px solid #f0eee8",
        display: "flex", alignItems: "flex-start", justifyContent: "space-between",
      }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <p style={{ margin: 0, fontSize: 11, color: "#B4B2A9", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 500 }}>Claim detail</p>
          <p style={{ margin: "4px 0 0", fontSize: 14, fontWeight: 500, color: "#2C2C2A", wordBreak: "break-all", lineHeight: 1.4 }}>{d.claimant_name || claim.file_name}</p>
        </div>
        <button onClick={onClose} style={{
          background: "none", border: "1px solid #e8e6e0", borderRadius: 8,
          width: 28, height: 28, cursor: "pointer", color: "#888780",
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0, marginLeft: 8,
          fontSize: 16, lineHeight: 1,
        }}>×</button>
      </div>

      <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #f0eee8" }}>
        <div style={{ marginBottom: 10 }}>
          <Badge status={dec.status} />
        </div>
        {dec.reason && (
          <p style={{ margin: 0, fontSize: 12, color: "#5F5E5A", lineHeight: 1.6 }}>{dec.reason}</p>
        )}
      </div>

      <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #f0eee8" }}>
        <p style={{ margin: "0 0 10px", fontSize: 12, fontWeight: 500, color: "#888780", textTransform: "uppercase", letterSpacing: "0.06em" }}>Extracted fields</p>
        {fields.map(([label, value]) => (
          <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8, gap: 12 }}>
            <span style={{ fontSize: 13, color: "#888780", flexShrink: 0 }}>{label}</span>
            <span style={{ fontSize: 13, color: value ? "#2C2C2A" : "#D3D1C7", textAlign: "right", fontFamily: label === "Policy number" ? "monospace" : "inherit", fontSize: label === "Policy number" ? 12 : 13 }}>
              {value || "—"}
            </span>
          </div>
        ))}
      </div>

      {d.description && (
        <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #f0eee8" }}>
          <p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 500, color: "#888780", textTransform: "uppercase", letterSpacing: "0.06em" }}>Description</p>
          <p style={{ margin: 0, fontSize: 13, color: "#5F5E5A", lineHeight: 1.65 }}>{d.description}</p>
        </div>
      )}

      {(v.flags?.length > 0 || v.inconsistencies?.length > 0 || v.missing_fields?.length > 0) && (
        <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #f0eee8" }}>
          <p style={{ margin: "0 0 10px", fontSize: 12, fontWeight: 500, color: "#888780", textTransform: "uppercase", letterSpacing: "0.06em" }}>Issues</p>
          {v.missing_fields?.map((f, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 7, alignItems: "flex-start" }}>
              <span style={{ fontSize: 11, background: "#FCEBEB", color: "#791F1F", border: "1px solid #F09595", borderRadius: 4, padding: "2px 6px", whiteSpace: "nowrap", flexShrink: 0, marginTop: 1 }}>missing</span>
              <span style={{ fontSize: 12, color: "#5F5E5A", lineHeight: 1.5 }}>{f}</span>
            </div>
          ))}
          {v.inconsistencies?.map((f, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 7, alignItems: "flex-start" }}>
              <span style={{ fontSize: 11, background: "#FCEBEB", color: "#791F1F", border: "1px solid #F09595", borderRadius: 4, padding: "2px 6px", whiteSpace: "nowrap", flexShrink: 0, marginTop: 1 }}>error</span>
              <span style={{ fontSize: 12, color: "#5F5E5A", lineHeight: 1.5 }}>{f}</span>
            </div>
          ))}
          {v.flags?.map((f, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 7, alignItems: "flex-start" }}>
              <span style={{ fontSize: 11, background: "#FAEEDA", color: "#633806", border: "1px solid #EF9F27", borderRadius: 4, padding: "2px 6px", whiteSpace: "nowrap", flexShrink: 0, marginTop: 1 }}>flag</span>
              <span style={{ fontSize: 12, color: "#5F5E5A", lineHeight: 1.5 }}>{f}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ padding: "1rem 1.25rem", marginTop: "auto" }}>
        <button
          onClick={() => { onDelete(claim.id); onClose(); }}
          style={{
            width: "100%", padding: "8px", fontSize: 13,
            background: "none", border: "1px solid #F09595",
            color: "#791F1F", borderRadius: 8, cursor: "pointer",
          }}
        >Delete claim</button>
      </div>
    </div>
  );
}

export default function App() {
  const [claims, setClaims]     = useState([]);
  const [summary, setSummary]   = useState({ ACCEPT: 0, FLAG: 0, REJECT: 0, total: 0 });
  const [filter, setFilter]     = useState("ALL");
  const [selected, setSelected] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast]       = useState(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const fetchAll = useCallback(async () => {
    try {
      const [cr, sr] = await Promise.all([fetch(`${API}/claims`), fetch(`${API}/claims/summary`)]);
      if (!cr.ok || !sr.ok) throw new Error();
      const cd = await cr.json();
      const sd = await sr.json();
      setClaims(cd.claims || []);
      setSummary(sd);
      setError(null);
    } catch {
      setError("Cannot reach the API. Make sure uvicorn is running on port 8000.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleUpload = async (file) => {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/claims`, { method: "POST", body: form });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Upload failed"); }
      const result = await res.json();
      showToast(`${file.name} → ${result.decision.status}`);
      fetchAll();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await fetch(`${API}/claims/${id}`, { method: "DELETE" });
      showToast("Claim deleted.");
      fetchAll();
    } catch {
      showToast("Delete failed.", "error");
    }
  };

  const filtered = filter === "ALL" ? claims : claims.filter(c => c.decision?.status === filter);

  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", background: "#fff" }}>

      {toast && (
        <div style={{
          position: "fixed", top: 16, right: 16, zIndex: 999,
          background: toast.type === "error" ? "#FCEBEB" : "#EAF3DE",
          color: toast.type === "error" ? "#791F1F" : "#27500A",
          border: `1px solid ${toast.type === "error" ? "#F09595" : "#97C459"}`,
          borderRadius: 10, padding: "10px 16px",
          fontSize: 13, fontWeight: 500, maxWidth: 300, boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
        }}>{toast.msg}</div>
      )}

      <Sidebar summary={summary} filter={filter} setFilter={setFilter} onUpload={handleUpload} uploading={uploading} />

      <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "1.5rem 1.5rem 1rem", borderBottom: "1px solid #f0eee8" }}>
          <h1 style={{ margin: 0, fontSize: 18, fontWeight: 500, color: "#2C2C2A" }}>
            {filter === "ALL" ? "All claims" : STATUS[filter]?.label || filter}
          </h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#888780" }}>
            {filtered.length} claim{filtered.length !== 1 ? "s" : ""}
          </p>
        </div>

        <div style={{ display: "flex", gap: 12, padding: "1rem 1.5rem", borderBottom: "1px solid #f0eee8" }}>
          <StatCard label="Total"    value={summary.total}  />
          <StatCard label="Accepted" value={summary.ACCEPT} accent="#639922" />
          <StatCard label="Flagged"  value={summary.FLAG}   accent="#BA7517" />
          <StatCard label="Rejected" value={summary.REJECT} accent="#E24B4A" />
        </div>

        {error && (
          <div style={{ margin: "1rem 1.5rem", background: "#FCEBEB", color: "#791F1F", border: "1px solid #F09595", borderRadius: 8, padding: "10px 14px", fontSize: 13 }}>
            {error}
          </div>
        )}

        <div style={{ flex: 1, overflowX: "auto" }}>
          {loading ? (
            <p style={{ padding: "3rem", textAlign: "center", color: "#B4B2A9", fontSize: 14 }}>Loading claims...</p>
          ) : filtered.length === 0 ? (
            <div style={{ padding: "4rem", textAlign: "center" }}>
              <svg width="40" height="40" viewBox="0 0 40 40" fill="none" style={{ margin: "0 auto 12px", display: "block", opacity: 0.25 }}>
                <rect x="8" y="4" width="24" height="32" rx="3" stroke="#2C2C2A" strokeWidth="2"/>
                <path d="M14 14h12M14 20h12M14 26h7" stroke="#2C2C2A" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <p style={{ margin: 0, fontSize: 14, color: "#B4B2A9" }}>
                {claims.length === 0 ? "No claims yet. Upload a PDF to get started." : "No claims match this filter."}
              </p>
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #f0eee8", background: "#faf9f7" }}>
                  {["Claimant / file", "Policy", "Amount", "Date", "Type", "Status", ""].map(h => (
                    <th key={h} style={{ padding: "9px 16px", textAlign: "left", fontWeight: 500, color: "#B4B2A9", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <ClaimRow key={c.id} claim={c} onClick={() => setSelected(c)} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>

      {selected && (
        <DetailPanel
          claim={selected}
          onClose={() => setSelected(null)}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}