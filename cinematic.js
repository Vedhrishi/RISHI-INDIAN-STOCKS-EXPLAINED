// Apple-style cinematic 3D scroll intro for RISHI: a procedurally-rendered gold coin
// (embossed with the brand mark - no external 3D asset exists for the characters, so
// this is built from real geometry/materials/lighting rather than faked).
// Scroll pins the hero and scrubs one full 360deg rotation; once done, headline + cards
// fade in. Falls back to a simple auto-rotating image on touch/low-power/reduced-motion.
// three/gsap are loaded on demand so phones taking the lightweight fallback never download them.
let THREE, gsap, ScrollTrigger;

const prefersReduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const isSmall = matchMedia('(max-width: 600px)').matches;
const canWebGL = (() => {
  try { return !!document.createElement('canvas').getContext('webgl2'); } catch { return false; }
})();

const root = document.getElementById('cine');
if (!root) { /* section not present on this page */ }
else if (!canWebGL || prefersReduced || isSmall) {
  runFallback();
} else {
  Promise.all([import('three'), import('gsap'), import('gsap/ScrollTrigger')]).then(([t, g, st]) => {
    THREE = t; gsap = g.default; ScrollTrigger = st.ScrollTrigger;
    gsap.registerPlugin(ScrollTrigger);
    (window.requestIdleCallback || (f => setTimeout(f, 300)))(runCinematic, { timeout: 1500 });
  }).catch(runFallback);
}

function runFallback() {
  const host = document.getElementById('cine-canvas');
  host.innerHTML = `<div id="cine-fallback">
    <img src="assets/coin_fallback.png" alt="RISHI gold coin">
    <div><p class="eyebrow" style="color:#ffc42e;font-weight:700;letter-spacing:.1em;text-transform:uppercase;font-size:13px">Indian Stocks Explained</p>
    <h1 style="font-size:clamp(28px,7vw,48px);margin:8px 0">A new animated money story <b style="color:#ffc42e">every day</b></h1></div></div>`;
  host.querySelectorAll('img').forEach(im => im.addEventListener('error', () => { im.style.display = 'none'; }));
  document.getElementById('cine').style.height = isSmall ? 'auto' : '100vh';
  const copy = document.getElementById('cine-copy'); if (copy) copy.style.display = 'none';
  const cards = document.getElementById('cine-cards'); if (cards) { cards.style.opacity = 1; cards.style.position = 'static'; cards.style.marginTop = '24px'; }
}

function runCinematic() {
  const canvasHost = document.getElementById('cine-canvas');
  const renderer = new THREE.WebGLRenderer({ antialias: devicePixelRatio < 1.5, alpha: false, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.toneMapping = THREE.ACESFilmicToneMapping; // avoids the flat/muddy default render
  renderer.toneMappingExposure = 1.15;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  canvasHost.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05060d);
  const camera = new THREE.PerspectiveCamera(32, innerWidth / innerHeight, 0.1, 100);
  camera.position.set(0, 0, 7);

  // --- the coin: a 2048px canvas-drawn emblem (crisp on retina) on a beveled metal disc ---
  // Plain MeshStandardMaterial (no clearcoat / no PMREM env capture) keeps this light enough
  // for real low-end/mobile GPUs - strong direct + rim lighting does the "product shot" work instead.
  const emblem = makeEmblemTexture();
  const edgeMat = new THREE.MeshStandardMaterial({ color: 0xd8a63a, metalness: 0.95, roughness: 0.35 });
  const faceMat = new THREE.MeshStandardMaterial({ map: emblem, color: 0xffffff, metalness: 0.85, roughness: 0.4 });
  const coinRadius = 1.55;
  const coinGeo = new THREE.CylinderGeometry(coinRadius, coinRadius, 0.22, 64, 1, false);
  coinGeo.rotateX(Math.PI / 2); // cylinder's axis defaults to Y (edge-on to camera); bake a 90deg
                                // turn into the geometry so the face points at the camera (+Z) and
                                // the existing coin.rotation.y spin correctly reveals both faces.
  replanarizeCapUVs(coinGeo, coinRadius); // CylinderGeometry's cap UVs are radial by default, which
                                           // rotates/smears a flat canvas texture - remap to planar.
  const coin = new THREE.Mesh(coinGeo, [edgeMat, faceMat, faceMat]);
  scene.add(coin);

  const key = new THREE.DirectionalLight(0xfff3d6, 2.6); key.position.set(4, 5, 6); scene.add(key);
  const rim = new THREE.DirectionalLight(0x8fb3ff, 1.2); rim.position.set(-5, -2, -4); scene.add(rim);
  const fill = new THREE.DirectionalLight(0xffe9b3, 0.6); fill.position.set(-2, 3, 5); scene.add(fill);
  scene.add(new THREE.HemisphereLight(0xfff6e0, 0x1a1420, 0.5)); // cheap gradient fill, no env capture needed

  renderer.initTexture(emblem); renderer.compile(scene, camera);   // pay shader-compile + texture-upload cost now, not on the first scroll

  function resize() {
    const w = canvasHost.clientWidth, h = canvasHost.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  resize(); addEventListener('resize', resize);

  // Time-based (not per-frame) so the float is identical at 60, 144 or 240 Hz; stops rendering once the pinned intro is off-screen.
  const cineEl = document.getElementById('cine');
  let lastT = 0, floatT = 0, ratio = renderer.getPixelRatio(), checked = 0, tickN = 0;
  renderer.setAnimationLoop(t => {
    const dt = Math.min((t - lastT) / 1000, 0.05); lastT = t;
    if (scrollY > cineEl.offsetHeight) return;
    // The page UI runs at the display's full rate; the 3D coin renders every Nth frame (N divides the refresh rate, so cadence stays even).
    const m = window.__motion || {}, hz = m.hz || 60, low = document.documentElement.dataset.perf === 'low';
    const n = low ? Math.max(2, Math.round(hz / 30)) : hz >= 100 ? Math.round(hz / 72) || 1 : 1;
    floatT += dt * 0.6;
    if (++tickN % n) return;
    coin.position.y = Math.sin(floatT) * 0.08; // gentle idle float, independent of scroll rotation
    if (++checked % 90 === 0) {                 // adaptive resolution: shed pixels first if frames are missing budget
      const want = document.documentElement.dataset.perf === 'low' ? 1 : Math.min(devicePixelRatio, 1.75);
      if (want !== ratio) { ratio = want; renderer.setPixelRatio(ratio); resize(); }
    }
    renderer.render(scene, camera);
  });

  // --- scroll choreography: pin, rotate one full turn, release into copy + cards ---
  const tl = gsap.timeline({
    scrollTrigger: { trigger: '#cine', start: 'top top', end: 'bottom bottom', scrub: matchMedia('(hover: hover) and (pointer: fine)').matches ? 0.25 : 0.6, pin: '#cine-pin' },
  });
  tl.to(coin.rotation, { y: Math.PI * 2, ease: 'none' }, 0)
    .to(coin.scale, { x: 1.35, y: 1.35, z: 1.35, ease: 'power1.inOut' }, 0)
    .to('#cine-scrolltip', { opacity: 0, duration: 0.08 }, 0)
    .to('#cine-copy .eyebrow', { opacity: 1, y: -8, duration: 0.12 }, 0.78)
    .to('#cine-copy h1', { opacity: 1, y: 0, duration: 0.14 }, 0.82)
    .to('#cine-copy p', { opacity: 1, duration: 0.14 }, 0.88)
    .to('#cine-cards', { opacity: 1, y: 0, duration: 0.14 }, 0.9)
    .to(coin.position, { z: -1.2, duration: 0.2, ease: 'power2.in' }, 0.9);
  gsap.set('#cine-copy h1, #cine-copy p', { y: 24 });
  gsap.set('#cine-cards', { y: 20 });
}

function replanarizeCapUVs(geometry, radius) {
  const pos = geometry.attributes.position, uv = geometry.attributes.uv;
  for (const group of geometry.groups) {
    if (group.materialIndex === 0) continue; // the side (edge) group - leave its UVs alone
    const start = group.start, count = group.count;
    const idx = geometry.index;
    for (let i = start; i < start + count; i++) {
      const vi = idx.getX(i);
      const x = pos.getX(vi), y = pos.getY(vi);
      uv.setXY(vi, x / (2 * radius) + 0.5, y / (2 * radius) + 0.5);
    }
  }
  uv.needsUpdate = true;
}

function makeEmblemTexture() {
  const size = 2048;
  const c = document.createElement('canvas'); c.width = c.height = size;
  const ctx = c.getContext('2d');
  const grad = ctx.createRadialGradient(size / 2, size / 2, size * 0.1, size / 2, size / 2, size * 0.5);
  grad.addColorStop(0, '#f5d27a'); grad.addColorStop(0.6, '#d9a93e'); grad.addColorStop(1, '#a9781f');
  ctx.fillStyle = grad; ctx.beginPath(); ctx.arc(size / 2, size / 2, size * 0.49, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#7a5518'; ctx.lineWidth = size * 0.012;
  for (let r = 0.46, i = 0; i < 2; i++, r -= 0.03) { ctx.beginPath(); ctx.arc(size / 2, size / 2, size * r, 0, Math.PI * 2); ctx.stroke(); }
  ctx.fillStyle = '#6b4a12'; ctx.font = `700 ${size * 0.32}px Georgia, serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('₹', size / 2, size * 0.46);
  ctx.font = `800 ${size * 0.075}px "Segoe UI", Arial, sans-serif`; ctx.letterSpacing = `${size * 0.012}px`;
  ctx.fillText('R I S H I', size / 2, size * 0.68);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  return tex;
}

// Sound toggle: a soft synthesized ambient pad (no external audio file exists yet),
// built with the Web Audio API so the control is genuinely functional, not decorative.
const soundBtn = document.getElementById('cine-sound');
if (soundBtn) {
  let ctx, nodes, playing = false;
  soundBtn.addEventListener('click', () => {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (!playing) {
      const master = ctx.createGain(); master.gain.value = 0; master.connect(ctx.destination);
      const freqs = [110, 165, 220];
      nodes = freqs.map(f => {
        const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = f;
        const g = ctx.createGain(); g.gain.value = 0.12;
        o.connect(g).connect(master); o.start(); return o;
      });
      master.gain.linearRampToValueAtTime(0.5, ctx.currentTime + 1.2);
      nodes.master = master;
      playing = true; soundBtn.textContent = '\u{1F50A}';
    } else {
      nodes.master.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.6);
      setTimeout(() => nodes.forEach(o => o.stop && o.stop()), 700);
      playing = false; soundBtn.textContent = '\u{1F507}';
    }
  });
}
