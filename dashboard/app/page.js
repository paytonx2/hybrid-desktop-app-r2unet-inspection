'use client';

import { useEffect, useState, useMemo } from 'react';
import { supabase } from '../lib/supabaseClient';

const ACCENT = '#4f46e5';
const BORDER = '#e2e8f0';
const TEXT_MAIN = '#1e293b';
const TEXT_MUTED = '#64748b';
const GOOD = '#059669';
const BAD = '#dc2626';

const PAGE_SIZE = 50;

export default function DashboardPage() {
  const [rows, setRows] = useState([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);

  // Initial load
  useEffect(() => {
    let cancelled = false;

    async function loadInitial() {
      const { data, error } = await supabase
        .from('inspections')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(PAGE_SIZE);

      if (!cancelled) {
        if (!error && data) setRows(data);
        setLoading(false);
      }
    }

    loadInitial();
    return () => { cancelled = true; };
  }, []);

  // Realtime subscription
  useEffect(() => {
    const channel = supabase
      .channel('inspections-realtime')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'inspections' },
        (payload) => {
          setRows((prev) => [payload.new, ...prev].slice(0, PAGE_SIZE));
        }
      )
      .subscribe((status) => {
        setConnected(status === 'SUBSCRIBED');
      });

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const stats = useMemo(() => {
    const total = rows.length;
    const missing = rows.filter((r) => r.status === 'MISSING').length;
    const good = total - missing;
    const devices = new Set(rows.map((r) => r.device_id)).size;
    return { total, missing, good, devices };
  }, [rows]);

  return (
    <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 900, color: TEXT_MAIN, margin: 0 }}>
            R2U-NET Inspection Dashboard
          </h1>
          <p style={{ color: TEXT_MUTED, marginTop: 4 }}>Live feed from all connected inspection stations</p>
        </div>
        <ConnectionBadge connected={connected} />
      </header>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        <StatCard label="Recent Records" value={stats.total} color={ACCENT} />
        <StatCard label="Good" value={stats.good} color={GOOD} />
        <StatCard label="Missing / Defect" value={stats.missing} color={BAD} />
        <StatCard label="Active Devices" value={stats.devices} color={TEXT_MAIN} />
      </section>

      <section style={{ background: '#fff', border: `1px solid ${BORDER}`, borderRadius: 16, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: `1px solid ${BORDER}`, fontWeight: 800, color: TEXT_MAIN }}>
          Latest Inspections
        </div>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: TEXT_MUTED }}>Loading...</div>
        ) : rows.length === 0 ? (
          <div style={{ padding: 40, textAlign: 'center', color: TEXT_MUTED }}>
            No records yet. Run an inspection on a connected device to see it appear here in real time.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f8fafc', textAlign: 'left', fontSize: 12, color: TEXT_MUTED }}>
                <Th>Time</Th>
                <Th>Device</Th>
                <Th>Source</Th>
                <Th>Model</Th>
                <Th>Status</Th>
                <Th>Pixels</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} style={{ borderTop: `1px solid ${BORDER}` }}>
                  <Td>{new Date(r.ts || r.created_at).toLocaleString()}</Td>
                  <Td>{r.device_id}</Td>
                  <Td>{r.source}</Td>
                  <Td>{r.model_type}</Td>
                  <Td>
                    <StatusPill status={r.status} />
                  </Td>
                  <Td>{r.pixel_count}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div style={{ background: '#fff', border: `1px solid ${BORDER}`, borderRadius: 14, padding: '18px 20px' }}>
      <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.5, color: TEXT_MUTED, textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ fontSize: 30, fontWeight: 900, color, marginTop: 6 }}>{value}</div>
    </div>
  );
}

function ConnectionBadge({ connected }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 14px',
        borderRadius: 999,
        background: connected ? '#ecfdf5' : '#fef2f2',
        color: connected ? GOOD : BAD,
        fontWeight: 700,
        fontSize: 13,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: connected ? GOOD : BAD,
          display: 'inline-block',
        }}
      />
      {connected ? 'Live' : 'Connecting...'}
    </div>
  );
}

function StatusPill({ status }) {
  const isMissing = status === 'MISSING';
  return (
    <span
      style={{
        padding: '3px 10px',
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 800,
        background: isMissing ? '#fef2f2' : '#ecfdf5',
        color: isMissing ? BAD : GOOD,
      }}
    >
      {isMissing ? '🚨 MISSING' : '✅ GOOD'}
    </span>
  );
}

function Th({ children }) {
  return <th style={{ padding: '10px 20px', fontWeight: 700 }}>{children}</th>;
}

function Td({ children }) {
  return <td style={{ padding: '10px 20px', fontSize: 14, color: TEXT_MAIN }}>{children}</td>;
}
