
import { Link } from "react-router-dom";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { useEffect, useMemo, useRef, useState } from "react";
import useReveal from "../hooks/useReveal.js";

/* =========================================================
   ORIGINAL GALAXY — PRESERVED
========================================================= */

const input = { x: 0, y: 0 };

const isMobile = () =>
  typeof window !== "undefined" && window.innerWidth < 768;

const prefersReduced = () =>
  typeof window !== "undefined" &&
  !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

const gauss = () =>
  (Math.random() + Math.random() + Math.random() - 1.5) / 1.5;

function buildGalaxy(count) {
  const ARMS = 4;
  const R = 10;
  const pos = new Float32Array(count * 3);
  const rnd = new Float32Array(count * 3);

  for (let i = 0; i < count; i++) {
    const roll = Math.random();
    let x, y, z;

    if (roll < 0.16) {
      const r = Math.pow(Math.random(), 1.8) * 2.4;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      x = r * Math.sin(ph) * Math.cos(th);
      y = r * Math.sin(ph) * Math.sin(th);
      z = r * Math.cos(ph) * 0.55;
    } else if (roll < 0.9) {
      const r = 0.8 + Math.pow(Math.random(), 0.8) * R;
      const arm = Math.floor(Math.random() * ARMS);
      const a = arm * ((Math.PI * 2) / ARMS) + r * 0.62;
      const spread = 0.12 + r * 0.075;
      x = Math.cos(a) * r + gauss() * spread;
      y = Math.sin(a) * r + gauss() * spread;
      z = gauss() * (0.04 + 0.5 * Math.exp(-r * 0.35));
    } else {
      const r = Math.pow(Math.random(), 0.6) * R * 1.25;
      const th = Math.random() * Math.PI * 2;
      x = Math.cos(th) * r;
      y = Math.sin(th) * r;
      z = gauss() * 1.4;
    }

    pos[i * 3] = x;
    pos[i * 3 + 1] = y;
    pos[i * 3 + 2] = z;
    rnd[i * 3] = Math.random();
    rnd[i * 3 + 1] = Math.random();
    rnd[i * 3 + 2] = Math.random();
  }

  return { pos, rnd };
}

function buildShell(count) {
  const pos = new Float32Array(count * 3);
  const seed = new Float32Array(count);

  for (let i = 0; i < count; i++) {
    const r = 28 + Math.random() * 20;
    const th = Math.random() * Math.PI * 2;
    const ph = Math.acos(2 * Math.random() - 1);
    pos[i * 3] = r * Math.sin(ph) * Math.cos(th);
    pos[i * 3 + 1] = r * Math.sin(ph) * Math.sin(th);
    pos[i * 3 + 2] = r * Math.cos(ph);
    seed[i] = Math.random();
  }

  return { pos, seed };
}

const NEBULA_VERT = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

const NEBULA_FRAG = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform float uTime;
  uniform float uScroll;
  uniform float uIntensity;
  uniform float uSquash;
  uniform float uRot;
  uniform float uZoom;
  uniform vec2 uRes;
  uniform vec2 uMouse;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
      mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x),
      f.y
    );
  }

  float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    mat2 m = mat2(0.8, -0.6, 0.6, 0.8);
    for (int i = 0; i < 5; i++) {
      v += a * noise(p);
      p = m * p * 2.0 + 7.3;
      a *= 0.5;
    }
    return v;
  }

  void main() {
    vec2 uv = vUv;
    vec2 p = (uv - 0.5) * vec2(uRes.x / uRes.y, 1.0);
    p += uMouse * 0.03;
    p /= uZoom;

    float c = cos(uRot);
    float s = sin(uRot);
    vec2 q = mat2(c, -s, s, c) * p;
    q.y *= uSquash;
    float r = length(q);

    vec2 w = vec2(
      fbm(p * 2.0 + uTime * 0.010),
      fbm(p * 2.0 + vec2(5.2, 1.3) - uTime * 0.012)
    );
    float cloud = fbm(p * 2.6 + w * 1.6 + uTime * 0.006);
    float fine = fbm(p * 8.0 + w * 2.0 - uTime * 0.010);

    float band = exp(-r * 1.6);
    float halo = exp(-length(p) * 1.1);
    float core = exp(-r * 7.0);
    float coreWide = exp(-r * 2.6);

    float lane = smoothstep(
      0.0, 0.22,
      abs(q.y - 0.03 * sin(q.x * 5.0) + (cloud - 0.5) * 0.1)
    );

    float glow = band * cloud * 0.9
               + coreWide * 0.22
               + core * 0.9
               + halo * cloud * 0.18;
    glow *= mix(0.35, 1.0, lane);
    glow += fine * band * 0.12;

    vec3 col = vec3(0.006, 0.006, 0.010);
    col += vec3(0.60, 0.62, 0.66) * glow * 0.55;
    col += vec3(0.95, 0.95, 0.97) * core * 0.45;

    float vig = 1.0 - smoothstep(0.35, 1.0, length(uv - 0.5) * 1.25);
    col *= 0.35 + 0.65 * vig;
    col *= uIntensity;
    col += (hash(gl_FragCoord.xy) - 0.5) / 200.0;

    gl_FragColor = vec4(max(col, 0.0), 1.0);
  }
`;

const GALAXY_VERT = /* glsl */ `
  uniform float uTime;
  uniform float uPixel;
  uniform float uIntensity;
  attribute vec3 aRand;
  varying float vAlpha;
  varying float vTint;

  void main() {
    vec3 p = position;
    float r = length(p.xy);
    float ang = atan(p.y, p.x);
    ang += uTime * (0.03 + 0.02 * exp(-r * 0.6));
    p.xy = vec2(cos(ang), sin(ang)) * r;
    p.z += sin(uTime * 0.3 + aRand.y * 6.2831) * 0.03;

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;

    float tw = 0.65 + 0.35 * sin(uTime * (0.8 + aRand.x * 2.0) + aRand.y * 6.2831);
    float core = exp(-r * 0.45);
    float size = 0.8 + 3.2 * pow(aRand.x, 3.0);

    gl_PointSize = clamp(size * (1.0 + core * 0.8) * uPixel * (9.0 / -mv.z), 1.0, 14.0 * uPixel);
    vAlpha = tw * (0.35 + 0.65 * aRand.z) * (0.5 + core * 1.1) * uIntensity;
    vTint = aRand.z;
  }
`;

const GALAXY_FRAG = /* glsl */ `
  precision highp float;
  varying float vAlpha;
  varying float vTint;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, d);
    a *= a;
    vec3 col = mix(vec3(0.78, 0.80, 0.86), vec3(1.0, 0.98, 0.95), vTint);
    gl_FragColor = vec4(col, a * vAlpha);
  }
`;

const SHELL_VERT = /* glsl */ `
  uniform float uTime;
  uniform float uPixel;
  attribute float aSeed;
  varying float vA;

  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_Position = projectionMatrix * mv;
    float tw = 0.5 + 0.5 * sin(uTime * (0.6 + aSeed * 2.5) + aSeed * 40.0);
    gl_PointSize = (0.7 + aSeed * aSeed * 2.2) * uPixel;
    vA = (0.25 + 0.75 * tw) * (0.3 + 0.7 * aSeed);
  }
`;

const SHELL_FRAG = /* glsl */ `
  precision highp float;
  varying float vA;
  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.0, d);
    gl_FragColor = vec4(vec3(0.9, 0.92, 0.96), a * vA);
  }
`;

const METEOR_VERT = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const METEOR_FRAG = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform float uOpacity;

  void main() {
    float along = pow(vUv.x, 3.0);
    float across = 1.0 - smoothstep(0.0, 0.5, abs(vUv.y - 0.5));
    float head = smoothstep(0.93, 1.0, vUv.x) * 1.5;
    float a = (along + head) * across * uOpacity;
    gl_FragColor = vec4(vec3(1.0), a);
  }
`;

function Meteor() {
  const mesh = useRef();
  const uniforms = useMemo(() => ({ uOpacity: { value: 0 } }), []);

  const s = useMemo(() => {
    const st = {};
    st.reset = () => {
      st.t = -(3 + Math.random() * 7);
      st.dur = 0.9 + Math.random() * 0.6;
      st.x = -10 + Math.random() * 14;
      st.y = 2 + Math.random() * 4;
      st.angle = -Math.PI * (0.08 + Math.random() * 0.14);
      st.dx = Math.cos(st.angle);
      st.dy = Math.sin(st.angle);
      st.dist = 8 + Math.random() * 4;
    };
    st.reset();
    st.t = -(1 + Math.random() * 5);
    return st;
  }, []);

  useFrame((_, delta) => {
    s.t += Math.min(delta, 0.05);

    if (s.t < 0) {
      uniforms.uOpacity.value = 0;
      return;
    }

    const p = s.t / s.dur;

    if (p >= 1) {
      uniforms.uOpacity.value = 0;
      s.reset();
      return;
    }

    if (mesh.current) {
      mesh.current.position.set(
        s.x + s.dx * s.dist * p,
        s.y + s.dy * s.dist * p,
        -1
      );
      mesh.current.rotation.z = s.angle;
    }

    uniforms.uOpacity.value = Math.sin(p * Math.PI);
  });

  return (
    <mesh ref={mesh} scale={[3.2, 0.03, 1]} frustumCulled={false}>
      <planeGeometry args={[1, 1]} />
      <shaderMaterial
        uniforms={uniforms}
        vertexShader={METEOR_VERT}
        fragmentShader={METEOR_FRAG}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

function GalaxyScene() {
  const gl = useThree((state) => state.gl);
  const group = useRef();
  const shell = useRef();
  const smooth = useRef({ s: 0, x: 0, y: 0 });

  const reduce = useMemo(() => prefersReduced(), []);
  const mobile = useMemo(() => isMobile(), []);
  const galaxy = useMemo(() => buildGalaxy(mobile ? 22000 : 60000), [mobile]);
  const stars = useMemo(() => buildShell(mobile ? 1200 : 2800), [mobile]);
  const pixel = Math.min(gl.getPixelRatio(), 1.75);

  const galaxyUniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uPixel: { value: pixel },
      uIntensity: { value: 0 },
    }),
    [pixel]
  );

  const shellUniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uPixel: { value: pixel },
    }),
    [pixel]
  );

  const nebulaUniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uScroll: { value: 0 },
      uIntensity: { value: 0 },
      uSquash: { value: 2.4 },
      uRot: { value: 0.42 },
      uZoom: { value: 1 },
      uRes: { value: new THREE.Vector2(1, 1) },
      uMouse: { value: new THREE.Vector2(0, 0) },
    }),
    []
  );

  useFrame((state, delta) => {
    const dt = Math.min(delta, 0.05);
    const t = reduce ? 30 : state.clock.elapsedTime;
    const max = Math.max(
      1,
      document.documentElement.scrollHeight - window.innerHeight
    );
    const rawScroll = Math.min(Math.max(window.scrollY / max, 0), 1);

    const sm = smooth.current;
    sm.s = THREE.MathUtils.damp(sm.s, rawScroll, 3, dt);
    sm.x = THREE.MathUtils.damp(sm.x, input.x, 2.2, dt);
    sm.y = THREE.MathUtils.damp(sm.y, input.y, 2.2, dt);

    const intro = 1 - Math.exp(-t * 0.9);
    const intensity = (0.25 + 0.75 * intro) * (1 - sm.s * 0.4);
    const camZ = 9.5 - sm.s * 3.0 + (1 - intro) * 8;
    const cam = state.camera;

    cam.position.set(sm.x * 0.9, sm.y * 0.5 + sm.s * 1.0, camZ);
    cam.lookAt(0, 0, 0);

    const rx = -1.15 + sm.s * 0.55 + sm.y * 0.06;
    const rz = 0.42 - sm.s * 0.25;

    if (group.current) {
      group.current.rotation.set(rx, sm.x * 0.08, rz, "ZXY");
    }

    if (shell.current) {
      shell.current.rotation.y = t * 0.004;
      shell.current.rotation.x = t * 0.0015;
    }

    galaxyUniforms.uTime.value = t;
    galaxyUniforms.uIntensity.value = intensity;
    shellUniforms.uTime.value = t;

    nebulaUniforms.uTime.value = t;
    nebulaUniforms.uScroll.value = sm.s;
    nebulaUniforms.uIntensity.value = intensity;
    nebulaUniforms.uSquash.value = 1 / Math.max(0.2, Math.abs(Math.cos(rx)));
    nebulaUniforms.uRot.value = rz;
    nebulaUniforms.uZoom.value = 9.5 / camZ;
    nebulaUniforms.uRes.value.set(state.size.width, state.size.height);
    nebulaUniforms.uMouse.value.set(sm.x, sm.y);
  });

  return (
    <>
      <color attach="background" args={["#020204"]} />

      <mesh frustumCulled={false} renderOrder={-10}>
        <planeGeometry args={[2, 2]} />
        <shaderMaterial
          uniforms={nebulaUniforms}
          vertexShader={NEBULA_VERT}
          fragmentShader={NEBULA_FRAG}
          depthTest={false}
          depthWrite={false}
        />
      </mesh>

      <points ref={shell} frustumCulled={false}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[stars.pos, 3]} />
          <bufferAttribute attach="attributes-aSeed" args={[stars.seed, 1]} />
        </bufferGeometry>
        <shaderMaterial
          uniforms={shellUniforms}
          vertexShader={SHELL_VERT}
          fragmentShader={SHELL_FRAG}
          transparent
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>

      <group ref={group}>
        <points frustumCulled={false}>
          <bufferGeometry>
            <bufferAttribute attach="attributes-position" args={[galaxy.pos, 3]} />
            <bufferAttribute attach="attributes-aRand" args={[galaxy.rnd, 3]} />
          </bufferGeometry>
          <shaderMaterial
            uniforms={galaxyUniforms}
            vertexShader={GALAXY_VERT}
            fragmentShader={GALAXY_FRAG}
            transparent
            depthWrite={false}
            blending={THREE.AdditiveBlending}
          />
        </points>
      </group>

      {!reduce && (
        <>
          <Meteor />
          <Meteor />
          <Meteor />
        </>
      )}
    </>
  );
}

function GalaxyBackground() {
  useEffect(() => {
    const onMove = (e) => {
      input.x = (e.clientX / window.innerWidth) * 2 - 1;
      input.y = -((e.clientY / window.innerHeight) * 2 - 1);
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  return (
    <>
      <style>{`
        html { scroll-behavior: smooth; }
        section[id] { scroll-margin-top: 5rem; }

        .stackpilot-galaxy {
          position: fixed;
          inset: 0;
          z-index: 0;
          overflow: hidden;
          pointer-events: none;
          background: #020204;
        }

        .stackpilot-galaxy canvas {
          display: block;
          width: 100%;
          height: 100%;
        }

        .stackpilot-galaxy::after {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background: radial-gradient(
            ellipse at center,
            transparent 25%,
            rgba(0, 0, 0, 0.18) 60%,
            rgba(0, 0, 0, 0.72) 100%
          );
        }

        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(22px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes marquee-scroll {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }

        .marquee-track { animation: marquee-scroll 32s linear infinite; }
        .marquee-track:hover { animation-play-state: paused; }

        .reveal {
          opacity: 0;
          transform: translateY(20px);
          transition:
            opacity 700ms ease,
            transform 700ms ease,
            background-color 300ms ease,
            border-color 300ms ease;
        }

        .reveal.is-visible { opacity: 1; transform: translateY(0); }

        .sp-spot { position: relative; overflow: hidden; }

        .sp-spot::before {
          content: "";
          position: absolute;
          inset: 0;
          opacity: 0;
          pointer-events: none;
          transition: opacity 300ms ease;
          background: radial-gradient(
            380px circle at var(--mx, 50%) var(--my, 50%),
            rgba(255, 255, 255, 0.13),
            transparent 60%
          );
        }

        .sp-spot:hover::before { opacity: 1; }
        .sp-spot > * { position: relative; }

        .sp-outline {
          border: 1px solid rgba(255,255,255,.13);
          background: rgba(255,255,255,.035);
          backdrop-filter: blur(12px);
          transition: border-color 250ms ease, background 250ms ease, transform 250ms ease;
        }

        .sp-outline:hover {
          border-color: rgba(255,255,255,.3);
          background: rgba(255,255,255,.065);
          transform: translateY(-3px);
        }

        @media (prefers-reduced-motion: reduce) {
          html { scroll-behavior: auto; }
          .marquee-track { animation: none; }
          .reveal { opacity: 1; transform: none; transition: none; }
          .sp-outline { transition: none; }
        }
      `}</style>

      <div className="stackpilot-galaxy" aria-hidden="true">
        <Canvas
          camera={{ position: [0, 0, 9.5], fov: 55, near: 0.1, far: 200 }}
          dpr={[1, 1.75]}
          gl={{
            antialias: false,
            alpha: false,
            powerPreference: "high-performance",
          }}
        >
          <GalaxyScene />
        </Canvas>
      </div>
    </>
  );
}

/* =========================================================
   ORIGINAL LOGO AND NAVIGATION
========================================================= */

function Logo() {
  return (
    <Link
      to="/"
      className="flex items-center gap-2 text-lg font-semibold tracking-tight"
    >
      <div className="w-7 h-7 rounded-md flex items-center justify-center font-bold bg-surface text-neutral-950">
        S
      </div>
      <span className="text-white">StackPilot</span>
    </Link>
  );
}

function NavBar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={
        "fixed top-0 inset-x-0 z-40 transition-all duration-300 " +
        (scrolled
          ? "bg-black/50 backdrop-blur-xl border-b border-white/10"
          : "bg-transparent border-b border-transparent")
      }
    >
      <div
        className={
          "max-w-7xl mx-auto px-6 sm:px-8 flex items-center justify-between transition-all duration-300 " +
          (scrolled ? "h-16" : "h-20")
        }
      >
        <Logo />

        <nav className="hidden md:flex items-center gap-8 text-sm text-ink-muted/50">
          <a href="#features" className="hover:text-white transition">Product</a>
          <a href="#how-it-works" className="hover:text-white transition">Workflow</a>
          <a href="#demo" className="hover:text-white transition">Demo</a>
          <a href="#faq" className="hover:text-white transition">FAQ</a>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="hidden sm:inline text-sm font-medium text-ink-muted/50 hover:text-white transition"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            className="text-sm font-medium bg-surface text-neutral-950 rounded-full px-5 py-2.5 hover:bg-neutral-200 transition"
          >
            Get started <span aria-hidden="true">↗</span>
          </Link>
        </div>
      </div>
    </header>
  );
}

/* =========================================================
   REUSABLE SECTION HEADING
========================================================= */

function SectionHeading({ eyebrow, title, description, center = false }) {
  const ref = useReveal();

  return (
    <div ref={ref} className={`reveal ${center ? "mx-auto text-center" : ""} max-w-3xl`}>
      <p className="mb-5 text-[10px] font-medium uppercase tracking-[0.24em] text-white/50">
        {eyebrow}
      </p>
      <h2 className="text-3xl sm:text-5xl lg:text-6xl font-medium tracking-[-0.055em] leading-[1.08] text-white">
        {title}
      </h2>
      {description && (
        <p className={`mt-5 max-w-2xl text-sm sm:text-base leading-7 text-ink-muted/50 ${center ? "mx-auto" : ""}`}>
          {description}
        </p>
      )}
    </div>
  );
}

/* =========================================================
   HERO
========================================================= */

function Hero() {
  const ref = useReveal();

  return (
    <section className="relative overflow-hidden px-6 sm:px-8 pt-36 sm:pt-44 pb-20 sm:pb-28">
      <div className="max-w-7xl mx-auto">
        <div ref={ref} className="reveal grid lg:grid-cols-[1.12fr_.88fr] gap-12 lg:gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-3 rounded-full border border-white/15 bg-black/30 px-4 py-2 backdrop-blur-md">
              <span className="w-1.5 h-1.5 rounded-full bg-surface animate-pulse" />
              <span className="text-[10px] sm:text-xs uppercase tracking-[0.16em] text-white/75">
                AI-assisted software planning
              </span>
            </div>

            <h1 className="mt-8 text-5xl sm:text-6xl lg:text-[76px] xl:text-[88px] font-medium tracking-[-0.065em] leading-[.99] text-white">
              From idea
              <br />
              <span className="text-white/45">to architecture.</span>
              <br />
              To execution.
            </h1>

            <p className="mt-7 max-w-xl text-base sm:text-lg leading-8 text-ink-muted/50">
              Turn your project idea into structured requirements, UML diagrams,
              organized tasks and a clearer delivery plan — all in one connected
              software planning workspace.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Link
                to="/register"
                className="group inline-flex items-center gap-3 rounded-full bg-surface px-6 py-3.5 text-sm font-medium text-black transition hover:-translate-y-0.5 hover:bg-neutral-200"
              >
                Start planning
                <span className="transition-transform group-hover:translate-x-1">↗</span>
              </Link>

              <a
                href="#features"
                className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-black/20 px-6 py-3.5 text-sm text-white/80 backdrop-blur-md transition hover:border-white/45 hover:text-white"
              >
                Explore the workspace <span>↓</span>
              </a>
            </div>

            <div className="mt-10 flex flex-wrap gap-x-5 gap-y-3 text-[10px] uppercase tracking-[.16em] text-white/45">
              <span>Requirements</span>
              <span>UML diagrams</span>
              <span>Kanban</span>
              <span>Project planning</span>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-[440px] lg:ml-auto">
            <div className="absolute -inset-8 rounded-full bg-surface/[0.035] blur-3xl" />
            <div className="relative rounded-2xl border border-white/15 bg-black/45 p-2.5 shadow-2xl shadow-black/40 backdrop-blur-xl">
              <video
                className="block aspect-video w-full rounded-xl object-contain bg-black"
                src="/StackPilot_video.mp4"
                autoPlay
                loop
                muted
                playsInline
                controls={false}
                disablePictureInPicture
                preload="auto"
                aria-label="StackPilot product walkthrough"
              />
              <div className="flex items-center justify-between gap-4 px-3 py-3">
                <div>
                  <p className="text-xs font-medium text-white">StackPilot walkthrough</p>
                  <p className="mt-1 text-[10px] text-white/45">A closer look at the workspace</p>
                </div>
                <span className="rounded-full border border-white/15 px-3 py-1 text-[10px] text-white/65">
                  Product demo
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   CAPABILITY MARQUEE
========================================================= */

function Marquee() {
  const items = [
    "SRS documentation",
    "Use case diagrams",
    "Class diagrams",
    "Sequence diagrams",
    "Activity diagrams",
    "Kanban boards",
    "Cost estimates",
    "Gantt timelines",
  ];

  return (
    <section className="relative overflow-hidden py-7">
      <div
        className="flex overflow-hidden"
        style={{
          WebkitMaskImage: "linear-gradient(to right, transparent, black 12%, black 88%, transparent)",
          maskImage: "linear-gradient(to right, transparent, black 12%, black 88%, transparent)",
        }}
      >
        {[0, 1].map((group) => (
          <div
            key={group}
            className="marquee-track flex shrink-0 items-center gap-8 pr-8"
            aria-hidden={group === 1 ? "true" : undefined}
          >
            {items.map((item, i) => (
              <span key={`${group}-${item}`} className="flex items-center gap-8 whitespace-nowrap">
                <span className="text-xs sm:text-sm text-white/55">{item}</span>
                <span className="text-white/30" aria-hidden="true">✳</span>
              </span>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

/* =========================================================
   FEATURE CARDS
========================================================= */

function FeatureCard({ number, title, desc, tags }) {
  const ref = useReveal();

  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
  };

  return (
    <article
      ref={ref}
      onMouseMove={onMove}
      className="reveal sp-spot sp-outline rounded-2xl p-6 sm:p-7"
    >
      <div className="flex items-start justify-between gap-4">
        <span className="font-mono text-xs tracking-wider text-white/40">{number}</span>
        <span className="text-xl text-white/35" aria-hidden="true">↗</span>
      </div>

      <h3 className="mt-8 text-xl font-medium tracking-tight text-white">{title}</h3>
      <p className="mt-3 text-sm leading-7 text-ink-muted/50">{desc}</p>

      <div className="mt-6 flex flex-wrap gap-2">
        {tags.map((tag) => (
          <span
            key={tag}
            className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-[10px] text-white/60"
          >
            {tag}
          </span>
        ))}
      </div>
    </article>
  );
}

function Features() {
  const features = [
    {
      number: "01",
      title: "Requirements & SRS",
      desc: "Move from a plain-language project idea to a more structured requirements document that makes the intended system easier to understand.",
      tags: ["Functional requirements", "Non-functional requirements", "SRS"],
    },
    {
      number: "02",
      title: "UML system design",
      desc: "Visualize the system before implementation. Explore how users, components and system behavior relate to one another.",
      tags: ["Use case", "Class", "Sequence", "Activity"],
    },
    {
      number: "03",
      title: "Kanban task management",
      desc: "Keep work organized in boards and tasks. Make progress, priorities and next steps easier to follow.",
      tags: ["Boards", "Tasks", "Workflow"],
    },
    {
      number: "04",
      title: "AI project analysis",
      desc: "Use AI-assisted analysis to review project context and help identify effort, feasibility considerations and potential risks.",
      tags: ["Project context", "Effort", "Risk review"],
    },
    {
      number: "05",
      title: "Cost & timeline planning",
      desc: "Build planning estimates for task costs and durations, and organize the schedule with a Gantt-style project timeline.",
      tags: ["PKR estimates", "Task duration", "Gantt"],
    },
    {
      number: "06",
      title: "Design & deployment docs",
      desc: "Bring architecture decisions and implementation planning into clearer technical documentation for the development journey.",
      tags: ["SDD", "Architecture", "Deployment"],
    },
  ];

  return (
    <section id="features" className="relative scroll-mt-24 px-6 sm:px-8 py-24 sm:py-32">
      <div className="max-w-7xl mx-auto">
        <SectionHeading
          eyebrow="One connected workspace"
          title={<>Every stage of software planning.<br /><span className="text-white/40">Connected in one place.</span></>}
          description="Go beyond a list of tickets. Bring requirements, system design, task organization and delivery planning into one workflow."
        />

        <div className="mt-12 sm:mt-16 grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
          {features.map((feature) => (
            <FeatureCard key={feature.number} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   HOW IT WORKS
========================================================= */

function Step({ number, title, desc, last = false }) {
  const ref = useReveal();

  return (
    <div ref={ref} className="reveal relative flex gap-5">
      <div className="relative flex flex-col items-center">
        <span className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/20 bg-black/60 text-xs font-medium text-white">
          {number}
        </span>
        {!last && <span className="mt-2 w-px flex-1 bg-surface/15" />}
      </div>

      <div className="pb-10">
        <h3 className="pt-2 text-lg font-medium text-white">{title}</h3>
        <p className="mt-2 max-w-lg text-sm leading-7 text-ink-muted/50">{desc}</p>
      </div>
    </div>
  );
}

function HowItWorks() {
  return (
    <section id="how-it-works" className="relative scroll-mt-24 px-6 sm:px-8 py-24 sm:py-32">
      <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[.9fr_1.1fr] lg:gap-24">
        <div>
          <SectionHeading
            eyebrow="The workflow"
            title={<>From the first idea to a <span className="text-white/40">structured plan.</span></>}
            description="StackPilot helps you organize the important decisions before and during development."
          />

          <Link
            to="/register"
            className="mt-8 inline-flex items-center gap-3 rounded-full border border-white/20 px-5 py-3 text-sm text-white/85 transition hover:border-white/45 hover:bg-surface/[0.05]"
          >
            Start a project <span>↗</span>
          </Link>
        </div>

        <div className="pt-1">
          <Step
            number="01"
            title="Describe your project"
            desc="Start with the problem you want to solve, the people who will use the system and the outcome you want to achieve."
          />
          <Step
            number="02"
            title="Clarify requirements"
            desc="Organize the project's requirements into a more understandable specification and define what the system needs to do."
          />
          <Step
            number="03"
            title="Visualize the system"
            desc="Use relevant UML diagrams to make system structure, interactions and workflows easier to communicate."
          />
          <Step
            number="04"
            title="Break work into tasks"
            desc="Organize implementation work into a Kanban workflow and keep task priorities and progress visible."
          />
          <Step
            number="05"
            title="Plan cost and delivery"
            desc="Estimate effort, task costs and durations, then use the plan to help organize the project schedule."
          />
          <Step
            number="06"
            title="Prepare for implementation"
            desc="Bring the technical design and deployment documentation together to support the next stage of development."
            last
          />
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   INTERACTIVE WORKFLOW PREVIEW
========================================================= */

function WorkflowPreview() {
  const [active, setActive] = useState(0);

  const tabs = [
    {
      name: "Requirements",
      title: "Start with clarity.",
      description: "Capture what the system needs to do before work is split into tasks.",
      lines: [
        ["FR-01", "User authentication"],
        ["FR-02", "Project workspace"],
        ["FR-03", "Task management"],
      ],
    },
    {
      name: "UML design",
      title: "Make structure visible.",
      description: "Use diagrams to communicate the system's components and interactions.",
      lines: [
        ["UML-01", "Use case diagram"],
        ["UML-02", "Class diagram"],
        ["UML-03", "Sequence diagram"],
      ],
    },
    {
      name: "Kanban",
      title: "Turn plans into work.",
      description: "Organize the work into manageable tasks and track each task's progress.",
      lines: [
        ["TASK-01", "Design database"],
        ["TASK-02", "Build API endpoints"],
        ["TASK-03", "Connect frontend"],
      ],
    },
  ];

  const current = tabs[active];

  return (
    <section className="relative px-6 sm:px-8 py-20 sm:py-28">
      <div className="mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2 lg:gap-20">
        <div>
          <SectionHeading
            eyebrow="See the workflow"
            title={<>Ideas become <span className="text-white/40">actionable work.</span></>}
            description="Switch between stages to explore how project information can be organized from requirements through implementation."
          />

          <div className="mt-8 flex flex-wrap gap-2">
            {tabs.map((tab, i) => (
              <button
                key={tab.name}
                type="button"
                onClick={() => setActive(i)}
                aria-pressed={active === i}
                className={`rounded-full px-4 py-2.5 text-xs transition ${
                  active === i
                    ? "bg-surface text-black"
                    : "border border-white/15 bg-black/20 text-white/65 hover:border-white/35 hover:text-white"
                }`}
              >
                {tab.name}
              </button>
            ))}
          </div>
        </div>

        <div className="sp-outline relative overflow-hidden rounded-2xl p-5 sm:p-8">
          <div className="flex items-center justify-between gap-3">
            <div className="flex gap-1.5">
              <span className="h-2 w-2 rounded-full bg-surface/25" />
              <span className="h-2 w-2 rounded-full bg-surface/25" />
              <span className="h-2 w-2 rounded-full bg-surface/25" />
            </div>
            <span className="text-[10px] uppercase tracking-[.18em] text-white/40">
              Illustrative preview
            </span>
          </div>

          <div className="mt-9">
            <p className="text-[10px] uppercase tracking-[.18em] text-white/45">
              {current.name}
            </p>
            <h3 className="mt-3 text-2xl sm:text-3xl font-medium tracking-tight text-white">
              {current.title}
            </h3>
            <p className="mt-3 max-w-md text-sm leading-7 text-ink-muted/50">
              {current.description}
            </p>
          </div>

          <div className="mt-8 space-y-3">
            {current.lines.map(([id, label], index) => (
              <div
                key={id}
                className="flex items-center gap-4 rounded-xl border border-white/10 bg-black/25 px-4 py-4 transition"
                style={{ animation: `fade-in-up 350ms ease both`, animationDelay: `${index * 70}ms` }}
              >
                <span className="font-mono text-[10px] text-white/40">{id}</span>
                <span className="flex-1 text-sm text-white/85">{label}</span>
                <span className="text-xs text-white/40">↗</span>
              </div>
            ))}
          </div>

          <p className="mt-5 text-[10px] leading-5 text-white/35">
            Example content for demonstrating the workflow; this preview is not connected to your saved project data.
          </p>
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   TECHNOLOGY
========================================================= */

function Technology() {
  const tech = ["React", "Vite", "FastAPI", "Python", "PostgreSQL", "Gemini AI", "Qdrant"];

  return (
    <section className="relative px-6 sm:px-8 py-16 sm:py-20">
      <div className="mx-auto max-w-7xl">
        <div className="text-center">
          <p className="text-[10px] uppercase tracking-[.22em] text-white/45">
            The technology behind the workspace
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            {tech.map((item) => (
              <span
                key={item}
                className="rounded-full border border-white/15 bg-black/20 px-4 py-2.5 text-xs text-white/70 transition hover:border-white/35 hover:text-white"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   FAQ
========================================================= */

function Faq() {
  const faqs = [
    {
      q: "What is StackPilot?",
      a: "StackPilot is an AI-assisted software planning workspace designed to bring project requirements, diagrams, task organization and delivery planning into a more connected workflow.",
    },
    {
      q: "Can it help with software requirements and UML?",
      a: "StackPilot is designed around structured requirements and software design workflows, including SRS documentation and UML diagram planning.",
    },
    {
      q: "Can I manage development tasks?",
      a: "Yes. StackPilot includes a board-and-task workflow intended to help organize work and track project progress.",
    },
    {
      q: "Are project costs guaranteed?",
      a: "No. Cost figures are estimates based on assumptions and the rates used. They should be reviewed and adjusted for the actual project, team and market.",
    },
    {
      q: "Does the landing page preview connect to my project?",
      a: "The interactive preview on this page is illustrative. Your actual saved boards, tasks and project data remain in the application workspace.",
    },
  ];

  return (
    <section id="faq" className="relative scroll-mt-24 px-6 sm:px-8 py-24 sm:py-28">
      <div className="mx-auto max-w-3xl">
        <SectionHeading
          eyebrow="Frequently asked questions"
          title={<>A few things worth <span className="text-white/40">knowing.</span></>}
          description="Understand what StackPilot is built to help with before you get started."
        />

        <div className="mt-10">
          {faqs.map((faq) => (
            <details
              key={faq.q}
              className="group border-b border-white/10 py-5 first:border-t"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-5 text-sm sm:text-base font-medium text-white">
                {faq.q}
                <span className="shrink-0 text-xl font-light text-white/45 transition-transform duration-300 group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="max-w-2xl pt-4 pr-8 text-sm leading-7 text-ink-muted/50">
                {faq.a}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   FINAL CTA
========================================================= */

function CtaBanner() {
  const ref = useReveal();

  return (
    <section className="relative px-6 sm:px-8 py-24 sm:py-32">
      <div
        ref={ref}
        className="reveal relative mx-auto max-w-7xl overflow-hidden rounded-3xl border border-white/15 bg-black/45 px-6 py-16 text-center backdrop-blur-xl sm:px-12 sm:py-24"
      >
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(255,255,255,0.10),transparent_60%)]" />

        <div className="relative z-10 mx-auto max-w-3xl">
          <p className="text-[10px] uppercase tracking-[.24em] text-white/50">
            Your next project starts here
          </p>

          <h2 className="mt-6 text-4xl sm:text-5xl lg:text-7xl font-medium leading-[1.04] tracking-[-.06em] text-white">
            Plan with purpose.
            <br />
            <span className="text-white/40">Build with confidence.</span>
          </h2>

          <p className="mx-auto mt-6 max-w-xl text-sm sm:text-base leading-7 text-ink-muted/50">
            Give your project a clearer structure — from the first requirements
            to tasks, design decisions and delivery planning.
          </p>

          <Link
            to="/register"
            className="mt-9 inline-flex items-center gap-3 rounded-full bg-surface px-7 py-4 text-sm font-medium text-black transition hover:-translate-y-0.5 hover:bg-neutral-200"
          >
            Get started with StackPilot <span>↗</span>
          </Link>
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   FOOTER
========================================================= */

function Footer() {
  return (
    <footer className="relative bg-black/45 px-6 sm:px-8 py-9 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-5 sm:flex-row">
        <Logo />

        <nav className="flex flex-wrap justify-center gap-x-5 gap-y-3 text-xs text-white/50">
          <a href="#features" className="transition hover:text-white">Product</a>
          <a href="#how-it-works" className="transition hover:text-white">Workflow</a>
          <a href="#demo" className="transition hover:text-white">Demo</a>
          <a href="#faq" className="transition hover:text-white">FAQ</a>
        </nav>

        <p className="text-center text-[10px] text-white/40">
          © {new Date().getFullYear()} StackPilot
        </p>
      </div>
    </footer>
  );
}

/* =========================================================
   LANDING PAGE
========================================================= */

export default function Landing() {
  useEffect(() => {
    const nodes = document.querySelectorAll(".reveal:not(.is-visible)");

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );

    nodes.forEach((node) => observer.observe(node));

    return () => observer.disconnect();
  }, []);

  return (
    <div className="relative min-h-screen overflow-clip bg-[#020204] text-white selection:bg-surface selection:text-black">
      <GalaxyBackground />

      <div className="relative z-10">
        <NavBar />
        <main>
          <Hero />
          <Marquee />
          <Features />
          <HowItWorks />
          <WorkflowPreview />

          <div id="demo" className="scroll-mt-24">
            <Technology />
          </div>

          <Faq />
          <CtaBanner />
        </main>
        <Footer />
      </div>
    </div>
  );
}
