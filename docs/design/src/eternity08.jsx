// Eternity 08 — animated OS walkthrough on the animations-v3 engine.
// All choreography keyed to useComposition().T and CUES; one tree, always mounted.
const { CompositionStage, useComposition, Shot, Captions, Easing, animate, interpolate, clamp,
  useTweaks, TweaksPanel, TweakSection, TweakToggle, TweakSlider, TweakRadio } = window;

// Token mirrors (hex needed for rgba/gradients/SVG); everything else uses var(--*).
const TK = { bg: '#161826', surface: '#232532', text: '#e9e9ed', accent: '#9184d9', a300: '#d2cefd', a400: '#b5abfc',
  a700: '#5d5294', a600: '#796cbf', a100: '#f5f4ff', a200: '#e7e5fe', a800: '#423a6a', a900: '#2b2741', n400: '#b2b6ca', n500: '#9397ab', n600: '#75798c', n700: '#595d6c', n800: '#3f424d', n900: '#292b31' };
const FONT = 'Inter, system-ui, sans-serif';
const MOTION = { enter: Easing.easeOutCubic, draw: Easing.easeInOutSine, pop: Easing.easeOutBack };
const tw = (T, start, end, from, to, ease) => animate({ from, to, start, end, ease: ease || MOTION.enter })(T);
const typed = (s, t, cps) => s.slice(0, Math.max(0, Math.floor(t * (cps || 24))));
const fadeRule = (c) => `linear-gradient(to right, transparent, ${c} 48px, ${c} calc(100% - 48px), transparent)`;
const nz = (seed, t) => 0.5 + 0.22 * Math.sin(t * 1.3 + seed) + 0.15 * Math.sin(t * 2.9 + seed * 2.1) + 0.08 * Math.sin(t * 6.1 + seed * 0.7);

// Per-section core placement; glides ±0.5s around each cue.
const ORDER = ['Boot', 'Setup', 'Login', 'Home', 'Assistant', 'Launcher', 'Files', 'Monitor', 'Settings'];
const CORE = {
  Boot: { x: 960, y: 500, s: 1, fast: 0 }, Setup: { x: 520, y: 540, s: 0.72, fast: 0 }, Login: { x: 960, y: 420, s: 0.78, fast: 0 },
  Home: { x: 960, y: 540, s: 0.5, fast: 0 }, Assistant: { x: 960, y: 420, s: 0.62, fast: 0.3 }, Launcher: { x: 960, y: 540, s: 0.42, fast: 0 },
  Files: { x: 1600, y: 540, s: 0.38, fast: 0 }, Monitor: { x: 960, y: 560, s: 0.46, fast: 0.12 }, Settings: { x: 520, y: 540, s: 0.5, fast: 0 },
};
function glide(T, CUES, total, key) {
  const input = [], output = [];
  ORDER.forEach((n, i) => {
    const c = CUES[n];
    if (i === 0) { input.push(c); output.push(CORE[n][key]); }
    else { input.push(c - 0.5, c + 0.5); output.push(CORE[ORDER[i - 1]][key], CORE[n][key]); }
  });
  const end = { x: 960, y: 540, s: 0.3, fast: 0 }[key];
  input.push(total - 1.8, total - 0.4); output.push(CORE.Settings[key], end);
  return interpolate(input, output, Easing.easeInOutCubic)(T);
}

// ——— Logo: fading 0 ring + upright ∞ drawn as a twisting Möbius ribbon; wordmark E = three stacked lines ———
const MOB_N = 150;
const MOB = (() => { const P = []; for (let i = 0; i <= MOB_N; i++) { const t = (i / MOB_N) * Math.PI * 2, d = 1 + Math.sin(t) ** 2; P.push({ t, x: 70 + 62 * Math.sin(t) * Math.cos(t) / d, y: 70 + 46 * Math.cos(t) / d }); } return P; })();
function Mobius({ T, size, draw, glow, ringColor, uid }) {
  const d = draw == null ? 1 : draw, phase = T * 1.4, quads = [];
  const lim = Math.floor(d * MOB_N);
  for (let i = 0; i < lim; i++) {
    const p0 = MOB[i], p1 = MOB[i + 1];
    const nx = -(p1.y - p0.y), ny = p1.x - p0.x, nl = Math.hypot(nx, ny) || 1;
    const w0 = 7.5 * Math.abs(Math.cos(p0.t)) ** 0.75, w1 = 7.5 * Math.abs(Math.cos(p1.t)) ** 0.75;
    const ax = p0.x + nx / nl * w0, ay = p0.y + ny / nl * w0, bx = p1.x + nx / nl * w1, by = p1.y + ny / nl * w1;
    const cx = p1.x - nx / nl * w1, cy = p1.y - ny / nl * w1, dx = p0.x - nx / nl * w0, dy = p0.y - ny / nl * w0;
    const sh = 0.5 + 0.5 * Math.sin(p0.t * 2 + phase), lit = 0.5 + 0.5 * Math.cos(p0.t + phase * 0.7);
    const mix = Math.round(45 + 55 * (0.55 * sh + 0.45 * lit));
    quads.push(<polygon key={i} points={`${ax},${ay} ${bx},${by} ${cx},${cy} ${dx},${dy}`} style={{ fill: `color-mix(in oklch, ${TK.a100} ${mix}%, ${TK.a600})`, stroke: `color-mix(in oklch, ${TK.a100} ${mix}%, ${TK.a600})`, strokeWidth: 0.6 }} />);
  }
  const k = MOB[Math.floor(((T * 0.22) % 1 + 1) % 1 * MOB_N)];
  const gid = 'ringfade-' + (uid || 'x');
  return (
    <svg width={size} height={size} viewBox="0 0 140 140" style={{ display: 'block', overflow: 'visible' }}>
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={ringColor || TK.n400} stopOpacity="0" /><stop offset="0.3" stopColor={ringColor || TK.n400} stopOpacity="1" /><stop offset="0.7" stopColor={ringColor || TK.n400} stopOpacity="1" /><stop offset="1" stopColor={ringColor || TK.n400} stopOpacity="0" /></linearGradient></defs>
      <circle cx="70" cy="70" r="64" fill="none" stroke={`url(#${gid})`} strokeWidth="2.2" strokeDasharray="402" strokeDashoffset={402 * (1 - d)} style={{ transform: 'rotate(-90deg)', transformOrigin: '70px 70px' }} />
      <g style={{ filter: glow ? `drop-shadow(0 0 ${6 * glow}px rgba(145,132,217,0.7))` : 'none' }}>{quads}</g>
      <circle cx={k.x} cy={k.y} r="2.2" style={{ fill: TK.a100, opacity: d >= 1 ? 0.9 : 0, filter: 'drop-shadow(0 0 4px rgba(245,244,255,0.9))' }} />
    </svg>
  );
}
// Wordmark: Michroma (wide geometric tech face) with a three-bar E
const TECH = "'Michroma', 'Inter', system-ui, sans-serif";
function Wordmark({ size, color, tracking }) {
  const ls = tracking == null ? 0.34 : tracking, cap = size * 0.72, stem = size * 0.1, ew = size * 0.74;
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', font: `400 ${size}px ${TECH}`, letterSpacing: `${ls}em`, color, lineHeight: 1, whiteSpace: 'nowrap' }}>
      <svg width={ew} height={cap} viewBox={`0 0 ${ew} ${cap}`} style={{ display: 'block', marginRight: size * ls, overflow: 'visible' }}>
        {[stem / 2, cap / 2, cap - stem / 2].map((y, i) => <line key={i} x1="0" x2={ew} y1={y} y2={y} strokeWidth={stem} style={{ stroke: color }} />)}
      </svg><span style={{ marginRight: `-${ls}em` }}>TERNITY</span>
    </div>
  );
}

// ——— The presence: concentric rings, ticks, glow ———
function Core({ T, x, y, s, fast, glow, total }) {
  const rings = [92, 134, 176, 214];
  const energy = 0.55 + 0.2 * Math.sin(T * Math.PI * 0.9) + fast * Math.sin(T * Math.PI * 4.4);
  const endFade = tw(T, total - 0.9, total - 0.05, 1, 0, MOTION.draw);
  const ticks = [];
  for (let i = 0; i < 72; i++) {
    const a = (i / 72) * Math.PI * 2, r1 = 240, r2 = i % 6 === 0 ? 228 : 234;
    const p = clamp((T - 2.0 - i * 0.012) / 0.6, 0, 1);
    ticks.push(<line key={i} x1={300 + Math.cos(a) * r1} y1={300 + Math.sin(a) * r1} x2={300 + Math.cos(a) * r2} y2={300 + Math.sin(a) * r2}
      style={{ stroke: i % 6 === 0 ? TK.a400 : TK.n700, opacity: p * (i % 6 === 0 ? 0.9 : 0.55) }} strokeWidth="1.5" />);
  }
  return (
    <div style={{ position: 'absolute', left: -300, top: -300, width: 600, height: 600, transform: `translate(${x}px,${y}px) scale(${s})`, opacity: endFade, pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', inset: 120, borderRadius: '50%', background: `radial-gradient(circle, rgba(145,132,217,${0.28 * energy * glow}) 0%, rgba(145,132,217,${0.08 * glow}) 45%, transparent 70%)`, transform: `scale(${1 + 0.08 * energy})`, opacity: clamp((T - 0.8) / 1.2, 0, 1) }} />
      <svg width="600" height="600" viewBox="0 0 600 600" style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
        <g style={{ transform: `rotate(${T * 1.5}deg)`, transformOrigin: '300px 300px' }}>{ticks}</g>
        {rings.map((r, i) => {
          const dir = i % 2 ? -1 : 1, p = clamp((T - 0.7 - i * 0.3) / 1.4, 0, 1);
          const dash = [0.62, 0.38, 0.16, 0.84, 0.3, 0.7, 0.08, 0.92][i * 2 % 8];
          return <circle key={r} cx="300" cy="300" r={r} fill="none" pathLength="1" strokeDasharray={`${dash * p} ${1 - dash * p}`} strokeLinecap="round"
            strokeWidth={i === 1 ? 2.5 : 1.25} style={{ stroke: i === 1 ? TK.accent : i === 3 ? TK.n600 : TK.a700, transform: `rotate(${dir * T * (10 + i * 7) - 90}deg)`, transformOrigin: '300px 300px', opacity: 0.55 + 0.45 * MOTION.draw(p) }} />;
        })}
        <circle cx="300" cy="300" r="5" style={{ fill: TK.a300, opacity: clamp((T - 0.3) / 0.6, 0, 1) * clamp((1.6 - T) / 0.4, 0, 1) }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center' }}><Mobius T={T} size={176} draw={tw(T, 1.3, 3.4, 0, 1, MOTION.draw)} glow={glow * (0.6 + 0.4 * energy)} uid="core" /></div>
    </div>
  );
}

function Rule({ T, start, end, y, width }) {
  const p = tw(T, start, end, 0, 1, MOTION.draw);
  return <div style={{ position: 'absolute', left: 960 - width / 2, top: y, width, height: 1, background: fadeRule('rgba(233,233,237,0.28)'), transform: `scaleX(${p})`, opacity: Math.min(1, p * 2) }} />;
}

// ——— Section helpers (each renders all the time, gated by <Shot>) ———
function Boot({ T, CUES }) {
  const t = T - CUES.Boot;
  const log = ['eternity-kernel 8.0.2 — secure boot verified', 'neural runtime · 4 cores online', 'memory graph restored · 1.2 GB', 'sensors · camera, mic, presence', 'realtime scheduler · 240 Hz', 'ready'];
  return (
    <Shot from={CUES.Boot} to={CUES.Setup}>
      <Rule T={T} start={0.2} end={1.3} y={500} width={1400} />
      <div style={{ position: 'absolute', left: 64, bottom: 64, display: 'flex', flexDirection: 'column', gap: 6, font: `400 13px ${FONT}`, color: TK.n600, opacity: tw(T, 5.6, 6.6, 1, 0) }}>
        {log.map((l, i) => <div key={i} style={{ opacity: tw(t, 0.9 + i * 0.55, 1.3 + i * 0.55, 0, 1), display: 'flex', gap: 10 }}><span style={{ color: TK.a700 }}>{String(i + 1).padStart(2, '0')}</span>{l}</div>)}
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 790, display: 'flex', justifyContent: 'center', opacity: tw(t, 3.4, 4.4, 0, 1) * tw(t, 6.0, 6.8, 1, 0), transform: `translateY(${tw(t, 3.4, 4.4, 10, 0)}px)` }}><Wordmark size={24} color={TK.text} /></div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 830, textAlign: 'center', font: `400 11px ${TECH}`, letterSpacing: '0.3em', color: TK.n500, opacity: tw(t, 4.0, 4.8, 0, 1) * tw(t, 6.0, 6.8, 1, 0) }}>PERSONAL OS · 08</div>
    </Shot>
  );
}

function Wave({ t, w, h, n, active, color }) {
  const bars = [];
  for (let i = 0; i < n; i++) {
    const a = active ? 0.25 + 0.75 * Math.abs(Math.sin(t * 7 + i * 0.9) * Math.sin(t * 2.3 + i * 0.4)) : 0.12;
    bars.push(<div key={i} style={{ width: 3, height: Math.max(3, a * h), borderRadius: 2, background: color || TK.accent, opacity: active ? 0.9 : 0.5 }} />);
  }
  return <div style={{ display: 'flex', alignItems: 'center', gap: 5, height: h, width: w }}>{bars}</div>;
}

function Setup({ T, CUES }) {
  const t = T - CUES.Setup;
  const methods = ['Face', 'Passphrase', 'Voice', 'PIN'];
  const out = tw(t, 10.2, 10.9, 1, 0);
  const row = (at) => ({ opacity: tw(t, at, at + 0.7, 0, 1) * out, transform: `translateY(${tw(t, at, at + 0.7, 14, 0)}px)` });
  return (
    <Shot from={CUES.Setup} to={CUES.Login}>
      <div style={{ position: 'absolute', left: 1000, top: 250, width: 640, display: 'flex', flexDirection: 'column', gap: 34 }}>
        <div style={row(0)}>
          <div style={{ font: `500 11px ${FONT}`, letterSpacing: '0.12em', textTransform: 'uppercase', color: TK.accent, marginBottom: 14 }}>First run · 1 of 3</div>
          <div style={{ font: `500 46px/1.1 ${FONT}`, letterSpacing: '-0.015em', color: TK.text, minHeight: 52 }}>{typed("Hello. I'm Eternity.", t - 0.3, 18)}<span style={{ opacity: Math.sin(t * 8) > 0 && t < 1.6 ? 1 : 0, color: TK.accent }}>|</span></div>
          <div style={{ font: `400 17px ${FONT}`, color: TK.n500, marginTop: 10, opacity: tw(t, 1.6, 2.2, 0, 1) }}>I run on this device, in real time. Let's set a few things.</div>
        </div>
        <div style={row(2.2)} className="field">
          <label>What should I call you?</label>
          <div className="input" style={{ height: 44, display: 'flex', alignItems: 'center', fontSize: 16, borderColor: t > 2.6 && t < 4.4 ? TK.accent : undefined }}>{typed('Maya', t - 2.9, 7)}<span style={{ opacity: t > 2.6 && t < 4.4 && Math.sin(t * 8) > 0 ? 1 : 0, color: TK.accent }}>|</span></div>
        </div>
        <div style={row(4.4)} className="field">
          <label>How would you like to unlock?</label>
          <div style={{ display: 'flex', gap: 10 }}>
            {methods.map((m, i) => { const on = t > 5.0 + i * 0.35; return <div key={m} className="btn btn-secondary" style={{ borderColor: on ? TK.accent : undefined, color: on ? TK.accent : TK.n400, background: on ? 'rgba(145,132,217,0.1)' : undefined, transform: `scale(${tw(t, 5.0 + i * 0.35, 5.4 + i * 0.35, 1, 1, MOTION.pop)})` }}><span style={{ width: 8, height: 8, borderRadius: 4, background: on ? TK.accent : TK.n700, display: 'inline-block' }} />{m}</div>; })}
          </div>
        </div>
        <div style={row(6.6)} className="field">
          <label>Voice sample · say “Eternity, it's me”</label>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <Wave t={t} w={420} h={44} n={48} active={t > 7.2 && t < 9.4} />
            <span style={{ font: `400 13px ${FONT}`, color: t > 9.4 ? TK.a300 : TK.n500 }}>{t > 9.4 ? 'Voiceprint stored · on device' : t > 7.2 ? 'Listening…' : ''}</span>
          </div>
        </div>
        <div style={{ ...row(9.5), display: 'flex', gap: 12 }}>
          <div className="btn btn-primary" style={{ padding: '10px 22px' }}>Continue</div>
          <div className="btn btn-ghost" style={{ color: TK.n500 }}>Skip for now</div>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 1000, top: 190, display: 'flex', gap: 8, opacity: out }}>
        {[0, 1, 2].map(i => <div key={i} style={{ width: i === 0 ? 36 : 14, height: 3, borderRadius: 2, background: i === 0 ? TK.accent : TK.n800 }} />)}
      </div>
    </Shot>
  );
}

function Login({ T, CUES }) {
  const t = T - CUES.Login;
  const scan = tw(t, 0.6, 2.6, -1, 1, MOTION.draw);
  const found = t > 2.7;
  const out = tw(t, 6.3, 7.0, 1, 0);
  return (
    <Shot from={CUES.Login} to={CUES.Home}>
      <div style={{ position: 'absolute', left: 960 - 110, top: 420 - 110, width: 220, height: 220, borderRadius: '50%', overflow: 'hidden', opacity: tw(t, 0.2, 0.8, 0, 1) * tw(t, 3.6, 4.2, 1, 0) }}>
        <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(circle at 50% 42%, ${TK.n800}, ${TK.n900})` }} />
        <div style={{ position: 'absolute', left: 70, top: 44, width: 80, height: 92, borderRadius: '46% 46% 42% 42%', background: TK.n700 }} />
        <div style={{ position: 'absolute', left: 30, top: 148, width: 160, height: 110, borderRadius: '50% 50% 0 0', background: TK.n700 }} />
        <div style={{ position: 'absolute', left: 0, right: 0, top: 110 + scan * 110, height: 2, background: fadeRule(TK.a300), boxShadow: `0 0 18px ${TK.accent}`, opacity: t < 2.7 ? 1 : 0 }} />
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 10, textAlign: 'center', font: `400 10px ${FONT}`, letterSpacing: '0.1em', color: TK.n500 }}>CAMERA</div>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 700, textAlign: 'center', font: `400 15px ${FONT}`, color: TK.n500, opacity: tw(t, 0.4, 1, 0, 1) * tw(t, 2.7, 3.1, 1, 0) }}>Looking for you…</div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 640, textAlign: 'center', opacity: tw(t, 2.9, 3.7, 0, 1) * out, transform: `translateY(${tw(t, 2.9, 3.7, 16, 0)}px)` }}>
        <div style={{ font: `500 52px/1.1 ${FONT}`, letterSpacing: '-0.015em', color: TK.text }}>Good evening, Maya.</div>
        <div style={{ font: `400 16px ${FONT}`, color: TK.n500, marginTop: 14, display: 'flex', justifyContent: 'center', gap: 20 }}>
          <span style={{ color: TK.a300 }}>Face recognised · 38 ms</span><span>3 things since you left</span>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 88, display: 'flex', justifyContent: 'center', gap: 10, opacity: tw(t, 1.2, 1.9, 0, 1) * out }}>
        {['Passphrase ⌘', 'Voice', 'PIN'].map(m => <span key={m} className="tag tag-outline" style={{ borderColor: TK.n700, color: TK.n500, padding: '6px 14px', whiteSpace: 'nowrap' }}>{m}</span>)}
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 56, textAlign: 'center', font: `400 12px ${FONT}`, color: TK.n600, opacity: tw(t, 1.2, 1.9, 0, 1) * out }}>Other ways to unlock</div>
    </Shot>
  );
}

function StatusBar({ T, CUES, total }) {
  const o = tw(T, CUES.Home - 0.2, CUES.Home + 0.6, 0, 1) * tw(T, total - 1.8, total - 1.2, 1, 0);
  const clock = `21:${String(42 + Math.floor((T - CUES.Home) / 20)).padStart(2, '0')}`;
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: 44, display: 'flex', alignItems: 'center', padding: '0 28px', font: `500 13px ${FONT}`, color: TK.n400, opacity: o }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}><Mobius T={T} size={20} glow={0} ringColor={TK.n500} uid="bar" /><Wordmark size={11} color={TK.text} tracking={0.2} /></div>
      <span style={{ marginLeft: 'auto', marginRight: 'auto', color: TK.text, fontVariantNumeric: 'tabular-nums' }}>{clock}</span>
      <div style={{ display: 'flex', gap: 22, fontVariantNumeric: 'tabular-nums' }}>
        <span><span style={{ color: TK.accent }}>●</span> live · {Math.round(38 + 6 * nz(3, T))} ms</span><span>NPU {Math.round(12 + 10 * nz(1, T))}%</span><span>Wi‑Fi</span><span>84%</span>
      </div>
    </div>
  );
}

function CommandBar({ T, CUES, total }) {
  const o = tw(T, CUES.Home + 0.9, CUES.Home + 1.6, 0, 1) * tw(T, total - 1.8, total - 1.2, 1, 0);
  const ta = T - CUES.Assistant;
  const inA = T >= CUES.Assistant && T < CUES.Launcher;
  const txt = inA ? typed('Move my 3pm to tomorrow and summarise the design doc', ta - 0.4, 26) : '';
  const focused = inA && ta < 3.2;
  return (
    <div style={{ position: 'absolute', left: 960 - 400, top: 950, width: 800, height: 54, borderRadius: 'var(--radius-lg)', background: TK.surface, boxShadow: focused ? `0 0 0 1px ${TK.accent}, 0 0 32px rgba(145,132,217,0.25)` : 'var(--shadow-sm)', display: 'flex', alignItems: 'center', padding: '0 20px', gap: 14, opacity: o, transform: `translateY(${tw(T, CUES.Home + 0.9, CUES.Home + 1.6, 20, 0)}px)` }}>
      <div style={{ width: 10, height: 10, borderRadius: 5, background: TK.accent, boxShadow: `0 0 12px ${TK.accent}`, opacity: 0.6 + 0.4 * Math.sin(T * 3) }} />
      <div style={{ font: `400 17px ${FONT}`, color: txt ? TK.text : TK.n600, flex: 1 }}>{txt || 'Ask Eternity, or type a command'}<span style={{ color: TK.accent, opacity: focused && Math.sin(T * 8) > 0 ? 1 : 0 }}>|</span></div>
      <span style={{ font: `400 12px ${FONT}`, color: TK.n600, border: `1px solid ${TK.n800}`, borderRadius: 6, padding: '2px 8px', whiteSpace: 'nowrap' }}>⌘ Space</span>
    </div>
  );
}

const WINDOWS = [
  { k: 'Calendar', title: 'Design review', body: 'Today · 15:00 — 16:00', meta: 'with Priya, Ola', a: -90 },
  { k: 'Mail', title: '3 new, 1 needs you', body: 'Ola: “shell spec v3 is ready for a read”', meta: 'summarised', a: 0 },
  { k: 'Now playing', title: 'Nocturne in E♭', body: 'Quiet focus · 42 min left', meta: '', a: 90 },
  { k: 'Focus', title: 'Writing block until 14:30', body: 'Notifications held · 6 queued', meta: '', a: 180 },
];
function Home({ T, CUES }) {
  const t = T - CUES.Home;
  const ta = T - CUES.Assistant;
  const dim = T >= CUES.Assistant ? tw(ta, 0.2, 1.2, 1, 0.1) : 1;
  const out = tw(T, CUES.Launcher - 0.5, CUES.Launcher + 0.1, 1, 0);
  const rot = t * 2.5;
  return (
    <Shot from={CUES.Home} to={CUES.Launcher + 0.2}>
      <svg width="1920" height="1080" style={{ position: 'absolute', inset: 0, opacity: tw(t, 0.6, 1.8, 0, 1) * out }}>
        <circle cx="960" cy="540" r="400" fill="none" pathLength="1" strokeDasharray="0.002 0.01" style={{ stroke: TK.n700, transform: `rotate(${rot}deg)`, transformOrigin: '960px 540px' }} strokeWidth="1" />
        <circle cx="960" cy="540" r="400" fill="none" pathLength="1" strokeDasharray={`${tw(t, 0.6, 2.4, 0, 0.18, MOTION.draw)} 1`} strokeLinecap="round" style={{ stroke: TK.accent, transform: `rotate(${rot * 1.4 - 90}deg)`, transformOrigin: '960px 540px', opacity: 0.6 }} strokeWidth="1.5" />
      </svg>
      {WINDOWS.map((w, i) => {
        const a = (w.a + rot) * Math.PI / 180, cx = 960 + Math.cos(a) * 440, cy = 540 + Math.sin(a) * 270;
        const p = tw(t, 1.0 + i * 0.25, 1.9 + i * 0.25, 0, 1, MOTION.pop);
        const yoff = T >= CUES.Assistant && i === 0 ? tw(ta, 3.4, 4.2, 0, -30) : 0;
        return (
          <div key={w.k} className="card elev-sm" style={{ position: 'absolute', left: cx - 150, top: cy - 60 + yoff, width: 300, opacity: Math.min(1, p) * (i === 0 ? 1 : dim) * out, transform: `scale(${0.85 + 0.15 * p})`, gap: 'var(--space-2)' }}>
            <div className="card-kicker">{w.k}</div>
            <div className="card-title">{T >= CUES.Assistant && i === 0 && ta > 4.0 ? 'Design review' : w.title}</div>
            <p className="card-body" style={{ color: T >= CUES.Assistant && i === 0 && ta > 4.0 ? TK.a300 : undefined }}>{T >= CUES.Assistant && i === 0 && ta > 4.0 ? 'Tomorrow · 15:00 — 16:00 · moved' : w.body}</p>
            {w.meta ? <div className="card-meta">{w.meta}</div> : null}
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 900, textAlign: 'center', font: `400 15px ${FONT}`, color: TK.n500, opacity: tw(t, 2.6, 3.4, 0, 1) * tw(t, 6.6, 7.4, 1, 0) * out }}>Everything stays in orbit — Eternity keeps what matters closest.</div>
    </Shot>
  );
}

function Assistant({ T, CUES }) {
  const t = T - CUES.Assistant;
  const reply = 'Done — Design review is now tomorrow at 15:00. Priya and Ola were told. The shell spec argues for one presence, not many apps; input stays sub‑50 ms end to end; everything personal is kept on the device.';
  const words = reply.split(' ');
  const n = Math.min(words.length, Math.max(0, Math.floor((t - 3.4) * 11)));
  const out = tw(t, 8.4, 9.0, 1, 0);
  const thinking = t > 2.6 && t < 3.4;
  return (
    <Shot from={CUES.Assistant} to={CUES.Launcher}>
      <div style={{ position: 'absolute', left: 960 - 400, top: 650, width: 800, opacity: tw(t, 3.2, 3.8, 0, 1) * out, transform: `translateY(${tw(t, 3.2, 3.9, 18, 0)}px)` }}>
        <div style={{ font: `400 19px/1.55 ${FONT}`, color: TK.text, minHeight: 90 }}>{words.slice(0, n).join(' ')}<span style={{ display: n < words.length ? 'inline-block' : 'none', width: 8, height: 18, background: TK.accent, marginLeft: 4, verticalAlign: '-3px', opacity: Math.sin(T * 10) > 0 ? 1 : 0.3 }} /></div>
        <div style={{ display: 'flex', gap: 10, marginTop: 22, opacity: tw(t, 6.6, 7.2, 0, 1) }}>
          <div className="btn btn-primary">Open spec</div><div className="btn btn-secondary">Undo move</div><div className="btn btn-ghost" style={{ color: TK.n500 }}>Tell Priya more</div>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 960 - 400, top: 620, width: 800, height: 1, background: fadeRule('rgba(233,233,237,0.22)'), opacity: tw(t, 3.2, 3.8, 0, 1) * out }} />
      <div style={{ position: 'absolute', left: 0, right: 0, top: 580, textAlign: 'center', font: `400 14px ${FONT}`, color: TK.n500, opacity: thinking ? 1 : 0 }}>Reading calendar, mail and the spec…</div>
      <div style={{ position: 'absolute', right: 40, top: 60, display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end', font: `400 12px ${FONT}`, color: TK.n600, fontVariantNumeric: 'tabular-nums', opacity: tw(t, 2.6, 3.2, 0, 1) * out }}>
        <span style={{ color: TK.a300 }}>realtime · on device</span>
        <span>first token {t > 3.4 ? '41 ms' : '—'}</span>
        <span>{t > 3.4 ? `${Math.round(170 + 30 * nz(5, T))} tok/s` : 'planning'}</span>
      </div>
    </Shot>
  );
}

const APPS = ['Files', 'Mail', 'Calendar', 'Notes', 'Music', 'Photos', 'Terminal', 'Browser', 'Messages', 'Code', 'Monitor', 'Settings'];
function Launcher({ T, CUES }) {
  const t = T - CUES.Launcher;
  const out = tw(t, 5.3, 6.0, 1, 0);
  return (
    <Shot from={CUES.Launcher} to={CUES.Files}>
      {APPS.map((a, i) => {
        const ang = (i / APPS.length) * Math.PI * 2 - Math.PI / 2 + t * 0.03;
        const p = tw(t, 0.3 + i * 0.07, 1.0 + i * 0.07, 0, 1, MOTION.pop), r = 150 + 200 * p;
        const x = 960 + Math.cos(ang) * r * 1.35, y = 540 + Math.sin(ang) * r;
        const sel = a === 'Files' && t > 3.2;
        return (
          <div key={a} style={{ position: 'absolute', left: x - 44, top: y - 44, width: 88, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, opacity: Math.min(1, p) * out, transform: `scale(${sel ? 1.12 : 1})` }}>
            <div style={{ width: 64, height: 64, borderRadius: 'var(--radius-lg)', background: TK.surface, boxShadow: sel ? `0 0 0 1px ${TK.accent}, 0 0 28px rgba(145,132,217,0.35)` : 'var(--shadow-sm)', display: 'grid', placeItems: 'center', font: `500 18px ${FONT}`, color: sel ? TK.a300 : TK.n400, letterSpacing: '0.04em' }}>{a.slice(0, 2)}</div>
            <span style={{ font: `400 12px ${FONT}`, color: sel ? TK.text : TK.n500 }}>{a}</span>
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: 0, right: 0, top: 100, textAlign: 'center', font: `400 15px ${FONT}`, color: TK.n500, opacity: tw(t, 1.6, 2.2, 0, 1) * out }}>Type to filter · <span style={{ color: TK.a300 }}>{typed('fil', t - 2.4, 6)}</span></div>
    </Shot>
  );
}

function Files({ T, CUES }) {
  const t = T - CUES.Files;
  const o = tw(t, 0, 0.7, 0, 1) * tw(t, 6.3, 7.0, 1, 0);
  const q = typed('photos from the Lisbon trip', t - 1.0, 20);
  const done = t > 2.6;
  return (
    <Shot from={CUES.Files} to={CUES.Monitor}>
      <div style={{ position: 'absolute', left: 1340, top: 540, width: 260, height: 1, background: fadeRule('rgba(145,132,217,0.5)'), opacity: o * tw(t, 0.4, 1, 0, 1) }} />
      <div style={{ position: 'absolute', left: 150, top: 230, width: 1190, height: 620, borderRadius: 'var(--radius-lg)', background: TK.surface, boxShadow: 'var(--shadow-md)', opacity: o, transform: `translateY(${tw(t, 0, 0.8, 24, 0)}px) scale(${tw(t, 0, 0.8, 0.96, 1)})`, display: 'grid', gridTemplateColumns: '220px 1fr', overflow: 'hidden' }}>
        <div style={{ padding: '24px 18px', borderRight: `1px solid ${TK.n900}`, display: 'flex', flexDirection: 'column', gap: 4, font: `400 14px ${FONT}`, color: TK.n400 }}>
          <div style={{ font: `500 11px ${FONT}`, letterSpacing: '0.1em', color: TK.n600, marginBottom: 10 }}>FILES</div>
          {['Recents', 'Desktop', 'Projects', 'Photos', 'Lisbon ★', 'Shared'].map((s, i) => <div key={s} style={{ padding: '7px 10px', borderRadius: 'var(--radius-sm)', background: i === 4 && done ? 'rgba(145,132,217,0.12)' : 'transparent', color: i === 4 && done ? TK.a300 : undefined }}>{s}</div>)}
        </div>
        <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="input" style={{ height: 46, display: 'flex', alignItems: 'center', gap: 12, fontSize: 16, borderColor: !done && t > 0.8 ? TK.accent : undefined, background: TK.bg }}>
            <span style={{ width: 8, height: 8, borderRadius: 4, background: TK.accent }} />
            <span style={{ color: q ? TK.text : TK.n600 }}>{q || 'Search by meaning…'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, font: `400 13px ${FONT}`, color: TK.n500, opacity: tw(t, 2.6, 3.1, 0, 1) }}>
            <span className="tag tag-accent">Grouped by Eternity</span><span>32 matches · 3 albums · March 2026</span><span style={{ marginLeft: 'auto', color: TK.a300 }}>{Math.round(24 + 4 * nz(2, T))} ms</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            {Array.from({ length: 8 }).map((_, i) => {
              const p = tw(t, 2.7 + i * 0.09, 3.3 + i * 0.09, 0, 1, MOTION.pop);
              const hue = [262, 250, 270, 240, 256, 266, 248, 258][i];
              return <div key={i} style={{ aspectRatio: '4 / 3', borderRadius: 'var(--radius-md)', background: `linear-gradient(${140 + i * 20}deg, oklch(0.36 0.04 ${hue}), oklch(0.22 0.03 ${hue}))`, opacity: p, transform: `scale(${0.92 + 0.08 * p})`, display: 'flex', alignItems: 'flex-end', padding: 10, font: `400 11px ${FONT}`, color: TK.n400 }}>IMG_{4120 + i * 7}</div>;
            })}
          </div>
          <div style={{ font: `400 14px ${FONT}`, color: TK.n500, opacity: tw(t, 4.2, 4.9, 0, 1) }}>Eternity: “Most of these are from the Alfama walk on the 14th. Want an album?”</div>
        </div>
      </div>
    </Shot>
  );
}

function Spark({ T, seed, w, h, color }) {
  const pts = [];
  for (let i = 0; i <= 80; i++) { const tt = T - 4 + i * 0.05; pts.push(`${(i / 80) * w},${h - nz(seed, tt) * h * 0.9 - 2}`); }
  return <svg width={w} height={h} style={{ display: 'block', overflow: 'visible' }}>
    <polyline points={pts.join(' ')} fill="none" strokeWidth="1.5" style={{ stroke: color }} />
    <circle cx={w} cy={h - nz(seed, T) * h * 0.9 - 2} r="3" style={{ fill: color }} />
  </svg>;
}
function Monitor({ T, CUES }) {
  const t = T - CUES.Monitor;
  const o = tw(t, 0, 0.7, 0, 1) * tw(t, 6.3, 7.0, 1, 0);
  const panels = [
    { k: 'CPU', seed: 1, unit: '%', base: 18, span: 20, x: 180, y: 220 }, { k: 'NPU', seed: 2, unit: '%', base: 34, span: 40, x: 1340, y: 220 },
    { k: 'Memory', seed: 3, unit: ' GB', base: 5.2, span: 1.4, x: 180, y: 680 }, { k: 'Input latency', seed: 4, unit: ' ms', base: 6, span: 4, x: 1340, y: 680 },
  ];
  return (
    <Shot from={CUES.Monitor} to={CUES.Settings}>
      <svg width="1920" height="1080" style={{ position: 'absolute', inset: 0, opacity: o }}>
        <circle cx="960" cy="560" r="300" fill="none" pathLength="1" strokeDasharray={`${0.34 + 0.1 * nz(2, T)} 1`} strokeLinecap="round" strokeWidth="3" style={{ stroke: TK.accent, transform: 'rotate(-90deg)', transformOrigin: '960px 560px', opacity: 0.8 }} />
        <circle cx="960" cy="560" r="300" fill="none" strokeWidth="1" style={{ stroke: TK.n800 }} />
      </svg>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 880, textAlign: 'center', font: `400 13px ${FONT}`, letterSpacing: '0.1em', color: TK.n500, opacity: o }}>NPU LOAD · <span style={{ color: TK.a300 }}>{Math.round(34 + 10 * nz(2, T))}%</span> · 240 Hz SCHEDULER · 0 DROPPED FRAMES</div>
      {panels.map((p, i) => {
        const v = p.base + p.span * nz(p.seed, T);
        return (
          <div key={p.k} style={{ position: 'absolute', left: p.x, top: p.y, width: 400, opacity: o * tw(t, 0.3 + i * 0.15, 0.9 + i * 0.15, 0, 1), transform: `translateY(${tw(t, 0.3 + i * 0.15, 0.9 + i * 0.15, 14, 0)}px)` }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ font: `500 11px ${FONT}`, letterSpacing: '0.1em', textTransform: 'uppercase', color: TK.n500 }}>{p.k}</span>
              <span style={{ font: `500 30px ${FONT}`, color: TK.text, fontVariantNumeric: 'tabular-nums' }}>{p.unit === ' GB' ? v.toFixed(1) : Math.round(v)}<span style={{ font: `400 14px ${FONT}`, color: TK.n500 }}>{p.unit}</span></span>
            </div>
            <Spark T={T} seed={p.seed} w={400} h={70} color={i === 1 ? TK.accent : TK.n400} />
            <div style={{ height: 1, background: fadeRule('rgba(233,233,237,0.14)'), marginTop: 10 }} />
          </div>
        );
      })}
    </Shot>
  );
}

function Toggle({ on }) {
  return <div style={{ width: 38, height: 22, borderRadius: 11, border: `1px solid ${on ? TK.accent : TK.n700}`, position: 'relative', background: on ? 'rgba(145,132,217,0.15)' : 'transparent' }}><div style={{ position: 'absolute', top: 3, left: on ? 19 : 3, width: 14, height: 14, borderRadius: 7, background: on ? TK.accent : TK.n600, transition: 'none' }} /></div>;
}
function Settings({ T, CUES, total }) {
  const t = T - CUES.Settings;
  const o = tw(t, 0, 0.7, 0, 1) * tw(T, total - 1.8, total - 1.2, 1, 0);
  const verb = tw(t, 2.2, 3.4, 0.62, 0.3, MOTION.draw);
  const rows = [
    ['Voice', <div className="seg" style={{ fontSize: 13 }}><span className="seg-opt" style={{ color: TK.accent, boxShadow: `inset 0 0 0 1px ${TK.accent}` }}>Calm</span><span className="seg-opt">Bright</span><span className="seg-opt">Off</span></div>],
    ['Verbosity', <div style={{ width: 240, height: 2, background: TK.n800, position: 'relative', borderRadius: 1 }}><div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${verb * 100}%`, background: TK.accent }} /><div style={{ position: 'absolute', left: `calc(${verb * 100}% - 7px)`, top: -6, width: 14, height: 14, borderRadius: 7, background: TK.a300 }} /></div>],
    ['Proactive suggestions', <Toggle on={true} />],
    ['Keep everything on device', <Toggle on={true} />],
    ['Share anonymous model telemetry', <Toggle on={t > 4.2 ? false : false} />],
    ['Unlock', <span style={{ font: `400 13px ${FONT}`, color: TK.n400 }}>Face · Passphrase · Voice · PIN</span>],
  ];
  return (
    <Shot from={CUES.Settings}>
      <div style={{ position: 'absolute', left: 1000, top: 200, width: 700, opacity: o, transform: `translateY(${tw(t, 0, 0.8, 20, 0)}px)` }}>
        <div style={{ font: `500 11px ${FONT}`, letterSpacing: '0.12em', textTransform: 'uppercase', color: TK.accent, marginBottom: 12 }}>Settings · Eternity</div>
        <div style={{ font: `500 36px ${FONT}`, letterSpacing: '-0.015em', color: TK.text, marginBottom: 30 }}>How she shows up</div>
        {rows.map((r, i) => (
          <div key={r[0]} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 0', background: fadeRule('rgba(233,233,237,0.1)') + ' no-repeat bottom / 100% 1px', font: `400 15px ${FONT}`, color: TK.text, opacity: tw(t, 0.5 + i * 0.12, 1.0 + i * 0.12, 0, 1) }}>
            <span>{r[0]}</span>{r[1]}
          </div>
        ))}
        <div style={{ font: `400 13px ${FONT}`, color: TK.n500, marginTop: 20, opacity: tw(t, 3.4, 4.0, 0, 1) }}>Changes apply instantly. Verbosity lowered — Eternity will answer in fewer words.</div>
      </div>
    </Shot>
  );
}

function Piece({ tweaks }) {
  const { T, CUES, authoredTotal: total } = useComposition();
  const glow = tweaks.glow;
  const x = glide(T, CUES, total, 'x'), y = glide(T, CUES, total, 'y'), s = glide(T, CUES, total, 's'), fast = glide(T, CUES, total, 'fast');
  const captions = [
    { at: CUES.Boot + 0.8, text: '01 · Boot' }, { at: CUES.Setup, text: '02 · First run' }, { at: CUES.Login, text: '03 · Unlock' }, { at: CUES.Home, text: '04 · Home — the presence is the desktop' },
    { at: CUES.Assistant, text: '05 · Ask' }, { at: CUES.Launcher, text: '06 · Launcher' }, { at: CUES.Files, text: '07 · Files — search by meaning' }, { at: CUES.Monitor, text: '08 · System' }, { at: CUES.Settings, text: '09 · Settings', until: total - 1.6 },
  ];
  const drift = Math.sin(T * 0.21) * 60;
  return (
    <div data-screen-label={`t=${Math.floor(T)}s`} style={{ position: 'absolute', inset: 0, fontFamily: FONT, color: TK.text, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 70% 60% at ${50 + drift / 20}% ${45 + drift / 40}%, #1b1e31 0%, ${TK.bg} 60%, #121421 100%)` }} />
      <div style={{ position: 'absolute', inset: 0, backgroundImage: `radial-gradient(circle at ${x}px ${y}px, rgba(145,132,217,${0.12 * glow}) 0%, transparent ${300 * s + 200}px)` }} />
      <Boot T={T} CUES={CUES} />
      <Setup T={T} CUES={CUES} />
      <Login T={T} CUES={CUES} />
      <Home T={T} CUES={CUES} />
      <Assistant T={T} CUES={CUES} />
      <Launcher T={T} CUES={CUES} />
      <Files T={T} CUES={CUES} />
      <Monitor T={T} CUES={CUES} />
      <Settings T={T} CUES={CUES} total={total} />
      <Core T={T} x={x} y={y} s={s} fast={fast} glow={glow} total={total} />
      <StatusBar T={T} CUES={CUES} total={total} />
      <CommandBar T={T} CUES={CUES} total={total} />
      <Rule T={T} start={total - 1.2} end={total - 0.5} y={540} width={1400} />
      <div style={{ position: 'absolute', inset: 0, background: TK.bg, opacity: tw(T, total - 0.5, total - 0.02, 0, 1, MOTION.draw), pointerEvents: 'none' }} />
      {tweaks.captions ? <Captions items={captions} style={{ left: 64, right: 'auto', bottom: 'auto', top: 60, textAlign: 'left', font: `500 12px ${FONT}`, letterSpacing: '0.14em', textTransform: 'uppercase', color: TK.n500, textShadow: 'none' }} /> : null}
    </div>
  );
}

function Eternity08App() {
  const [t, setTweak] = useTweaks(window.TWEAK_DEFAULTS);
  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <CompositionStage width={1920} height={1080} scenes={window.OM_SCENES} playback={window.OM_PLAYBACK} bg={TK.bg}>
        <Piece tweaks={t} />
      </CompositionStage>
      <TweaksPanel>
        <TweakSection label="Presence" />
        <TweakSlider label="Glow intensity" value={t.glow} min={0.3} max={1.8} step={0.1} onChange={(v) => setTweak('glow', v)} />
        <TweakToggle label="Scene captions" value={t.captions} onChange={(v) => setTweak('captions', v)} />
        <TweakSection label="Editor" />
        <TweakToggle label="Motion editor" value={t.motionEditor} onChange={(v) => setTweak('motionEditor', v)} />
      </TweaksPanel>
    </div>
  );
}
window.Eternity08App = Eternity08App;
