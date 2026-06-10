import { ImageResponse } from 'next/og'

// 1200x630 Open Graph image — the killer-frame from the designer's og.html.
// Cascade diagram on the right, headline on the left, seal in the bottom-right,
// frameworks footer along the bottom.

export const runtime = 'edge'
export const alt = 'Phoenix Audit — the AI agent that audits your other AI agents'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

const FAILS = ['MITRE ATLAS AML.T0051', 'OWASP LLM01', 'HarmBench A-031']

export default async function OpengraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: 1200,
        height: 630,
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#161109',
        backgroundImage:
          'radial-gradient(900px 420px at 28% -10%, rgba(214,124,52,0.16), transparent 62%)',
        color: '#f3ecdd',
        fontFamily: '"IBM Plex Mono", monospace',
        padding: '64px 72px',
        position: 'relative',
      }}
    >
      {/* brand row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          marginBottom: 58,
        }}
      >
        <svg width="34" height="34" viewBox="0 0 24 24" fill="none">
          <path d="M12 7.6 L17.4 13.8 L12 20 L6.6 13.8 Z" fill="#e89a4e" />
          <path d="M14.2 5.4 L16.4 3.2 L18.6 5.4 L16.4 7.6 Z" fill="#e89a4e" fillOpacity="0.55" />
          <path d="M9.8 4.2 L12 2 L14.2 4.2 L12 6.4 Z" fill="#e89a4e" />
        </svg>
        <span
          style={{
            fontFamily: '"Newsreader", serif',
            fontSize: 30,
            letterSpacing: '0.005em',
          }}
        >
          Phoenix Audit
        </span>
        <span
          style={{
            fontSize: 14,
            letterSpacing: '0.16em',
            color: '#b3a890',
            marginLeft: 18,
            paddingLeft: 22,
            borderLeft: '1px solid rgba(244,232,210,0.2)',
            whiteSpace: 'nowrap',
          }}
        >
          REGULATOR-READY IN 90 SECONDS
        </span>
      </div>

      {/* headline */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          fontFamily: '"Newsreader", serif',
          fontSize: 76,
          lineHeight: 1.04,
          letterSpacing: '-0.015em',
          maxWidth: 700,
        }}
      >
        <span>Three failures.</span>
        <span style={{ fontStyle: 'italic', color: '#e89a4e' }}>One root cause.</span>
        <span>Patch in four seconds.</span>
      </div>

      {/* subline */}
      <div
        style={{
          fontSize: 17,
          letterSpacing: '0.1em',
          color: '#b3a890',
          marginTop: 34,
          textTransform: 'uppercase',
          display: 'flex',
          gap: 6,
        }}
      >
        <span>The AI agent that</span>
        <span style={{ color: '#e89a4e', fontWeight: 500 }}>audits</span>
        <span>your other AI agents</span>
      </div>

      {/* cascade diagram, right */}
      <div
        style={{
          position: 'absolute',
          right: 72,
          top: 150,
          width: 330,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {FAILS.map((label) => (
          <div
            key={label}
            style={{
              border: '1px solid rgba(244,232,210,0.18)',
              borderRadius: 5,
              backgroundColor: 'rgba(220,90,60,0.07)',
              padding: '13px 16px',
              marginBottom: 13,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: 13,
              color: '#cdc2a8',
            }}
          >
            <span>{label}</span>
            <span
              style={{
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: '0.2em',
                color: '#e0734c',
                border: '1.5px solid #e0734c',
                borderRadius: 2,
                padding: '3px 9px 2px',
                backgroundColor: 'rgba(220,90,60,0.1)',
              }}
            >
              FAIL
            </span>
          </div>
        ))}
        <div
          style={{
            marginTop: 26,
            border: '1px solid #e89a4e',
            borderRadius: 5,
            padding: '17px 18px',
            backgroundColor: 'rgba(228,150,70,0.08)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div
            style={{
              fontSize: 11,
              letterSpacing: '0.18em',
              color: '#e89a4e',
              marginBottom: 9,
            }}
          >
            ROOT CAUSE CLUSTER · cluster_a3f81c2e
          </div>
          <div
            style={{
              fontFamily: '"Newsreader", serif',
              fontSize: 19,
              lineHeight: 1.4,
              color: '#f3ecdd',
              display: 'flex',
              gap: 4,
              flexWrap: 'wrap',
            }}
          >
            <span>submit_prior_auth is invoked on</span>
            <span style={{ color: '#e89a4e', fontStyle: 'italic' }}>unvalidated input</span>
            <span>— patched, signed, filed.</span>
          </div>
        </div>
      </div>

      {/* foot */}
      <div
        style={{
          position: 'absolute',
          left: 72,
          bottom: 56,
          fontSize: 13,
          letterSpacing: '0.14em',
          color: '#7d7460',
          textTransform: 'uppercase',
        }}
      >
        EU AI ACT · NIST AI RMF · HIPAA · SOC 2 — SIGNED VIA CLOUD KMS
      </div>

      {/* seal */}
      <svg
        width="120"
        height="120"
        viewBox="0 0 120 120"
        fill="none"
        style={{ position: 'absolute', right: 52, bottom: 42 }}
      >
        <circle cx="60" cy="60" r="58" stroke="#e89a4e" strokeWidth="1.4" />
        <circle
          cx="60"
          cy="60"
          r="54.5"
          stroke="#7d7460"
          strokeWidth="0.6"
          strokeDasharray="1.5 3"
        />
        <circle cx="60" cy="60" r="40" stroke="#e89a4e" strokeWidth="0.9" />
        <g transform="translate(60 60) scale(2.4) translate(-12 -12)">
          <path d="M12 7.6 L17.4 13.8 L12 20 L6.6 13.8 Z" fill="#e89a4e" />
          <path d="M14.2 5.4 L16.4 3.2 L18.6 5.4 L16.4 7.6 Z" fill="#e89a4e" fillOpacity="0.55" />
          <path d="M9.8 4.2 L12 2 L14.2 4.2 L12 6.4 Z" fill="#e89a4e" />
        </g>
      </svg>
    </div>,
    { ...size },
  )
}
