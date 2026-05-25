/**
 * bg-anim.js — Canvas starfield + nebula + meteor animation
 * Insert <canvas id="bgCanvas"></canvas> before </body>
 */
(function () {
  const canvas = document.getElementById("bgCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let W, H;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  /* ── Nebula blobs ─────────────────────────────────── */
  const BLOBS = [
    { x: 0.12, y: 0.18, r: 0.38, cr: [31, 169, 144],  a: 0.10, dx: 0.00008, dy: 0.00005 },
    { x: 0.85, y: 0.75, r: 0.32, cr: [212, 168, 67],  a: 0.08, dx:-0.00006, dy: 0.00007 },
    { x: 0.50, y: 0.45, r: 0.50, cr: [80,  50, 160],  a: 0.06, dx: 0.00004, dy:-0.00004 },
    { x: 0.75, y: 0.10, r: 0.25, cr: [100, 60, 200],  a: 0.07, dx:-0.00005, dy: 0.00006 },
  ];

  function drawBlobs(t) {
    for (const b of BLOBS) {
      // slow drift
      const px = ((b.x + b.dx * t) % 1.2 - 0.1 + 1.1) % 1.2 - 0.1;
      const py = ((b.y + b.dy * t) % 1.2 - 0.1 + 1.1) % 1.2 - 0.1;
      const cx = px * W;
      const cy = py * H;
      const radius = b.r * Math.min(W, H);
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
      const [r, gr, bl] = b.cr;
      g.addColorStop(0,   `rgba(${r},${gr},${bl},${b.a})`);
      g.addColorStop(1,   `rgba(${r},${gr},${bl},0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  /* ── Stars ────────────────────────────────────────── */
  const STAR_COUNT = 120;
  const stars = Array.from({ length: STAR_COUNT }, (_, i) => ({
    x:    Math.random(),
    y:    Math.random(),
    size: Math.random() * 1.6 + 0.3,
    // twinkle phase & speed
    phase: Math.random() * Math.PI * 2,
    freq:  0.0003 + Math.random() * 0.0008,
    // base opacity
    base:  0.35 + Math.random() * 0.5,
    // subtle drift
    vx:   (Math.random() - 0.5) * 0.000012,
    vy:   (Math.random() - 0.5) * 0.000008,
    // only first 15 stars get the expensive radial glow
    glow: i < 15,
  }));

  function drawStars(t) {
    for (const s of stars) {
      s.x = ((s.x + s.vx) % 1 + 1) % 1;
      s.y = ((s.y + s.vy) % 1 + 1) % 1;
      const alpha = s.base * (0.55 + 0.45 * Math.sin(s.phase + s.freq * t));
      const px = s.x * W;
      const py = s.y * H;
      // glow for limited stars only
      if (s.glow) {
        const g = ctx.createRadialGradient(px, py, 0, px, py, s.size * 3);
        g.addColorStop(0,   `rgba(255,245,220,${alpha * 0.6})`);
        g.addColorStop(1,   `rgba(255,245,220,0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(px, py, s.size * 3, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.beginPath();
      ctx.arc(px, py, s.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,245,220,${alpha})`;
      ctx.fill();
    }
  }

  /* ── Meteors ──────────────────────────────────────── */
  class Meteor {
    constructor() { this.reset(true); }
    reset(initial) {
      // random spawn along top/right edge
      this.active  = !initial;
      this.wait    = (initial ? 0 : 3000) + Math.random() * 6000;
      this.elapsed = 0;
      this.duration = 500 + Math.random() * 400;
      const angle  = (30 + Math.random() * 25) * Math.PI / 180; // 30-55° downward
      const speed  = 0.55 + Math.random() * 0.35; // fraction of screen/duration
      this.x0 = Math.random() * 0.8;
      this.y0 = Math.random() * 0.3;
      this.dx = Math.cos(angle) * speed;
      this.dy = Math.sin(angle) * speed;
      this.len = 0.06 + Math.random() * 0.08;
      this.spawned = false;
    }
    draw(dt, t) {
      if (!this.spawned) {
        this.elapsed += dt;
        if (this.elapsed < this.wait) return;
        this.spawned  = true;
        this.elapsed  = 0;
        this.active   = true;
      }
      if (!this.active) return;
      this.elapsed += dt;
      const prog = Math.min(this.elapsed / this.duration, 1);
      const alpha = prog < 0.2 ? prog / 0.2 : prog > 0.7 ? (1 - prog) / 0.3 : 1;
      const x1 = (this.x0 + this.dx * prog) * W;
      const y1 = (this.y0 + this.dy * prog) * H;
      const x0 = x1 - this.dx * this.len * W;
      const y0 = y1 - this.dy * this.len * H;
      const g  = ctx.createLinearGradient(x0, y0, x1, y1);
      g.addColorStop(0, `rgba(255,245,220,0)`);
      g.addColorStop(1, `rgba(255,245,220,${alpha * 0.9})`);
      ctx.strokeStyle = g;
      ctx.lineWidth   = 1.5;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
      if (prog >= 1) this.reset(false);
    }
  }

  const METEORS = Array.from({ length: 5 }, () => new Meteor());

  /* ── Main loop ────────────────────────────────────── */
  let last = 0;
  const FRAME_INTERVAL = 33; // ~30 fps cap
  function frame(ts) {
    const dt = ts - last;
    if (dt < FRAME_INTERVAL) {
      requestAnimationFrame(frame);
      return;
    }
    last = ts;

    ctx.clearRect(0, 0, W, H);

    // Background base
    ctx.fillStyle = "#07091a";
    ctx.fillRect(0, 0, W, H);

    drawBlobs(ts);
    drawStars(ts);

    for (const m of METEORS) m.draw(dt, ts);

    requestAnimationFrame(frame);
  }

  requestAnimationFrame((ts) => { last = ts; frame(ts); });
})();
