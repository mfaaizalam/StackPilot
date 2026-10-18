import { Link } from "react-router-dom";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import { useEffect, useMemo, useRef, useState } from "react";
import useReveal from "../hooks/useReveal.js";

/* =========================================================
   SHARED HELPERS
========================================================= */

// Mouse position (-1..1), written by a window listener because the
// canvas has pointer-events: none and R3F's own pointer would stay at 0.
const input = { x: 0, y: 0 };

const isMobile = () =>
  typeof window !== "undefined" && window.innerWidth < 768;

const prefersReduced = () =>
  typeof window !== "undefined" &&
  !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Soft bell-curve random in [-1, 1]
const gauss = () => (Math.random() + Math.random() + Math.random() - 1.5) / 1.5;

/* =========================================================
   GALAXY DATA (built once, rendered entirely on the GPU)
========================================================= */

function buildGalaxy(count) {
  const ARMS = 4;
  const R = 10;
  const pos = new Float32Array(count * 3);
  const rnd = new Float32Array(count * 3);

  for (let i = 0; i < count; i++) {
    const roll = Math.random();
    let x, y, z;

    if (roll < 0.16) {
      // dense central bulge
      const r = Math.pow(Math.random(), 1.8) * 2.4;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      x = r * Math.sin(ph) * Math.cos(th);
      y = r * Math.sin(ph) * Math.sin(th);
      z = r * Math.cos(ph) * 0.55;
    } else if (roll < 0.9) {
      // spiral arms
      const r = 0.8 + Math.pow(Math.random(), 0.8) * R;
      const arm = Math.floor(Math.random() * ARMS);
      const a = arm * ((Math.PI * 2) / ARMS) + r * 0.62;
      const spread = 0.12 + r * 0.075;
      x = Math.cos(a) * r + gauss() * spread;
      y = Math.sin(a) * r + gauss() * spread;
      z = gauss() * (0.04 + 0.5 * Math.exp(-r * 0.35));
    } else {
      // loose halo / field stars
      const r = Math.pow(Math.random(), 0.6) * R * 1.25;
      const th = Math.random() * Math.PI * 2;
      x = Math.cos(th) * r;
      y = Math.sin(th) * r;
      z = gauss() * 1.4;
    }

    pos[i * 3] = x;
    pos[i * 3 + 1] = y;
    pos[i * 3 + 2] = z;

    rnd[i * 3] = Math.random(); // size
    rnd[i * 3 + 1] = Math.random(); // twinkle phase
    rnd[i * 3 + 2] = Math.random(); // brightness
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

/* =========================================================
   SHADERS
========================================================= */

// Full-screen nebula: domain-warped dust, tilted galactic band,
// bright core, dust lane. Shape follows the star disc's tilt.
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

    // tilt: rotate then squash to match the 3D disc
    float c = cos(uRot);
    float s = sin(uRot);
    vec2 q = mat2(c, -s, s, c) * p;
    q.y *= uSquash;
    float r = length(q);

    // domain-warped dust clouds
    vec2 w = vec2(
      fbm(p * 2.0 + uTime * 0.010),
      fbm(p * 2.0 + vec2(5.2, 1.3) - uTime * 0.012)
    );
    float cloud = fbm(p * 2.6 + w * 1.6 + uTime * 0.006);
    float fine  = fbm(p * 8.0 + w * 2.0 - uTime * 0.010);

    float band     = exp(-r * 1.6);
    float halo     = exp(-length(p) * 1.1);
    float core     = exp(-r * 7.0);
    float coreWide = exp(-r * 2.6);

    // dark dust lane running through the disc
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

    // dither to kill banding in the dark gradients
    col += (hash(gl_FragCoord.xy) - 0.5) / 200.0;

    gl_FragColor = vec4(max(col, 0.0), 1.0);
  }
`;

// Main galaxy: every star twinkles, bulge spins faster than the rim,
// size and brightness vary per star, additive blending for glow.
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

    // rigid spin + extra spin near the core
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

// Distant background stars
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
    float along  = pow(vUv.x, 3.0);
    float across = 1.0 - smoothstep(0.0, 0.5, abs(vUv.y - 0.5));
    float head   = smoothstep(0.93, 1.0, vUv.x) * 1.5;
    float a = (along + head) * across * uOpacity;
    gl_FragColor = vec4(vec3(1.0), a);
  }
`;

/* =========================================================
   SHOOTING STARS
========================================================= */

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

/* =========================================================
   GALAXY SCENE
========================================================= */

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

    // scroll progress across the whole page (0..1)
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

    // camera: parallax with mouse, dolly in on scroll, fly-in on load
    const camZ = 9.5 - sm.s * 3.0 + (1 - intro) * 8;
    const cam = state.camera;
    cam.position.set(sm.x * 0.9, sm.y * 0.5 + sm.s * 1.0, camZ);
    cam.lookAt(0, 0, 0);

    // disc tilts toward face-on as you scroll
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

      {/* Full-screen nebula */}
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

      {/* Distant stars */}
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

      {/* The galaxy itself */}
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
        section[id] { scroll-margin-top: 4rem; }

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
          to   { opacity: 1; transform: translateY(0); }
        }

        @keyframes marquee-scroll {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
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

        /* cursor-following highlight on feature cards */
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

        @media (prefers-reduced-motion: reduce) {
          html { scroll-behavior: auto; }
          .marquee-track { animation: none; }
          .reveal { opacity: 1; transform: none; transition: none; }
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
   LOGO AND NAVIGATION
========================================================= */

function Logo() {
  return (
    <Link
      to="/"
      className="flex items-center gap-2 text-lg font-semibold tracking-tight"
    >
      <div className="w-7 h-7 rounded-md flex items-center justify-center font-bold bg-white text-neutral-950">
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
          "max-w-6xl mx-auto px-6 sm:px-8 flex items-center justify-between transition-all duration-300 " +
          (scrolled ? "h-16" : "h-20")
        }
      >
        <Logo />

        <nav className="hidden md:flex items-center gap-8 text-sm text-neutral-300">
          <a href="#features" className="hover:text-white transition">
            Product
          </a>
          <a href="#how-it-works" className="hover:text-white transition">
            How it works
          </a>
          <a href="#faq" className="hover:text-white transition">
            FAQ
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="hidden sm:inline text-sm font-medium text-neutral-300 hover:text-white transition"
          >
            Sign in
          </Link>

          <Link
            to="/register"
            className="text-sm font-medium bg-white text-neutral-950 rounded-lg px-4 py-2 hover:bg-neutral-200 transition"
          >
            Get started
          </Link>
        </div>
      </div>
    </header>
  );
}

/* =========================================================
   HERO
========================================================= */

function StackVisual() {
  return (
    <div className="relative w-full max-w-md mx-auto lg:mx-0">
      <div className="absolute -bottom-24 -right-16 w-80 h-80 rounded-full bg-white/[0.04] blur-3xl" />
      <div className="absolute -top-16 -left-10 w-64 h-64 rounded-full bg-neutral-400/[0.05] blur-3xl" />

      <div className="relative rounded-2xl border border-white/10 bg-black/60 backdrop-blur-xl p-2 shadow-2xl shadow-black/40">
        <video
          className="w-full h-auto rounded-xl"
          src="/StackPilot_video.mp4"
          autoPlay
          loop
          muted
          playsInline
          controls
        >
          Your browser does not support the video tag.
        </video>
      </div>
    </div>
  );
}

function Hero() {
  return (
    <section className="relative bg-transparent text-white overflow-hidden pt-40 pb-28 px-6 sm:px-8">
      <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
        <div style={{ animation: "fade-in-up 0.8s ease both" }}>
          <span className="inline-flex items-center gap-2 text-xs font-medium tracking-wide text-neutral-300 border border-white/15 bg-white/5 rounded-full px-3 py-1 mb-6 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
            AI-assisted project management
          </span>

          <h1
            className="text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.08] text-transparent bg-clip-text bg-gradient-to-b from-white to-neutral-400"
            style={{ textShadow: "0 0 60px rgba(255,255,255,0.12)" }}
          >
            Plan the stack.
            <br />
            Ship the product.
          </h1>

          <p className="mt-5 text-neutral-300 text-lg leading-relaxed max-w-lg">
            Boards, tasks, and an AI that actually reads your project — so you
            spend less time reorganizing tickets and more time building.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Link
              to="/register"
              className="bg-white text-neutral-950 rounded-lg px-5 py-3 text-sm font-medium hover:bg-neutral-200 transition shadow-[0_0_40px_rgba(255,255,255,0.18)]"
            >
              Get started free
            </Link>

            <a
              href="#how-it-works"
              className="text-sm font-medium text-neutral-300 hover:text-white transition"
            >
              See how it works →
            </a>
          </div>
        </div>

        <StackVisual />
      </div>
    </section>
  );
}

/* =========================================================
   TECHNOLOGY MARQUEE
========================================================= */

function Marquee() {
  const stack = ["React", "FastAPI", "PostgreSQL", "Gemini AI", "Qdrant", "Vite"];
  const items = [...stack, ...stack];

  const maskStyle = {
    WebkitMaskImage:
      "linear-gradient(to right, transparent, black 12%, black 88%, transparent)",
    maskImage:
      "linear-gradient(to right, transparent, black 12%, black 88%, transparent)",
  };

  return (
    <section className="relative bg-black/45 backdrop-blur-md border-y border-white/10 py-8 overflow-hidden">
      <p className="text-center text-xs uppercase tracking-wide text-neutral-400 mb-5">
        Built on a stack teams already trust
      </p>

      <div className="flex overflow-hidden" style={maskStyle}>
        <div className="marquee-track flex gap-10 pr-10 shrink-0">
          {items.map((name, i) => (
            <span
              key={`${name}-${i}`}
              className="text-neutral-300 font-medium text-sm whitespace-nowrap"
            >
              {name}
            </span>
          ))}
        </div>

        <div className="marquee-track flex gap-10 pr-10 shrink-0" aria-hidden="true">
          {items.map((name, i) => (
            <span
              key={`dup-${name}-${i}`}
              className="text-neutral-300 font-medium text-sm whitespace-nowrap"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

/* =========================================================
   FEATURES
========================================================= */

function FeatureCard({ icon, title, desc }) {
  const ref = useReveal();

  const onMove = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
  };

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      className="reveal sp-spot rounded-2xl border border-white/10 bg-white/[0.045] backdrop-blur-md p-7 hover:bg-white/[0.07] hover:border-white/25"
    >
      <div className="w-10 h-10 rounded-lg bg-white text-neutral-950 flex items-center justify-center mb-5">
        {icon}
      </div>

      <h3 className="font-semibold text-white mb-2">{title}</h3>

      <p className="text-sm text-neutral-300 leading-relaxed">{desc}</p>
    </div>
  );
}

function Features() {
  return (
    <section
      id="features"
      className="relative max-w-6xl mx-auto px-6 sm:px-8 py-28"
    >
      <div className="max-w-xl mb-14">
        <h2 className="text-3xl font-semibold tracking-tight text-white">
          Everything a project needs, nothing it doesn't
        </h2>

        <p className="mt-3 text-neutral-300 leading-relaxed">
          One workspace to organize the work, and an AI layer that understands
          it well enough to help you make decisions.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <FeatureCard
          title="Boards & tasks"
          desc="Kanban boards, columns, and tasks that stay out of your way — built for how dev teams actually track work."
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <rect x="3" y="4" width="6" height="16" rx="1.5" strokeWidth="1.8" />
              <rect x="9.5" y="4" width="6" height="10" rx="1.5" strokeWidth="1.8" />
              <rect x="16" y="4" width="5" height="13" rx="1.5" strokeWidth="1.8" />
            </svg>
          }
        />

        <FeatureCard
          title="AI project analysis"
          desc="One click on any board produces a report on feasibility, effort, risk, and where the project stands — not just a task count."
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path
                d="M4 19V6a1 1 0 0 1 1-1h9l6 6v8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1Z"
                strokeWidth="1.8"
              />
              <path d="M8 13h8M8 16.5h5" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          }
        />

        <FeatureCard
          title="Ask StackPilot"
          desc="A chat built into every board, so context about your project is always one question away."
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M4 5h16v11H8l-4 4V5Z" strokeWidth="1.8" strokeLinejoin="round" />
            </svg>
          }
        />
      </div>
    </section>
  );
}

/* =========================================================
   HOW IT WORKS
========================================================= */

function Step({ n, title, desc }) {
  const ref = useReveal();

  return (
    <div ref={ref} className="reveal flex gap-5">
      <span className="shrink-0 w-9 h-9 rounded-full border border-white/20 bg-white/5 flex items-center justify-center text-xs font-semibold text-neutral-300 tabular-nums">
        {n}
      </span>

      <div>
        <h4 className="font-medium text-white pt-1.5">{title}</h4>

        <p className="mt-1.5 text-sm text-neutral-300 leading-relaxed max-w-sm">
          {desc}
        </p>
      </div>
    </div>
  );
}

function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="relative bg-black/35 backdrop-blur-sm border-y border-white/10 py-28"
    >
      <div className="max-w-6xl mx-auto px-6 sm:px-8 grid lg:grid-cols-2 gap-16">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-white">
            From idea to shipped, in order
          </h2>

          <p className="mt-3 text-neutral-300 leading-relaxed max-w-md">
            StackPilot follows the actual life of a project — set it up, break
            it down, then check in on it.
          </p>
        </div>

        <div className="space-y-10">
          <Step
            n="1"
            title="Create a board"
            desc="Spin up a board for your project and lay out the columns that match how your team works."
          />
          <Step
            n="2"
            title="Break it into tasks"
            desc="Add tasks under each column, assign them, and track them as work moves forward."
          />
          <Step
            n="3"
            title="Ask StackPilot to analyze it"
            desc="Get a report on where the project stands — feasibility, effort, and what to fix next."
          />
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
      q: "Is StackPilot free to use?",
      a: "You can create an account and start using boards and tasks at no cost while StackPilot is in early access.",
    },
    {
      q: "What does the AI project analysis look at?",
      a: "It reads your board's tasks and progress to produce a report on feasibility, effort, and suggestions — not just a status count.",
    },
    {
      q: "Is the chat assistant available yet?",
      a: "It's visible in every board and being actively built. You'll see a note if you try a feature that isn't live yet.",
    },
  ];

  return (
    <section id="faq" className="relative max-w-3xl mx-auto px-6 sm:px-8 py-28">
      <h2 className="text-3xl font-semibold tracking-tight text-white mb-10">
        Questions, answered
      </h2>

      <div className="divide-y divide-white/10 border-t border-b border-white/10">
        {faqs.map((f) => (
          <details key={f.q} className="group py-5">
            <summary className="flex items-center justify-between cursor-pointer list-none text-white font-medium">
              {f.q}
              <span className="text-neutral-400 group-open:rotate-45 transition-transform text-xl leading-none">
                +
              </span>
            </summary>

            <p className="mt-3 text-sm text-neutral-300 leading-relaxed">{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

/* =========================================================
   CALL TO ACTION
========================================================= */

function CtaBanner() {
  return (
    <section className="relative bg-black/55 backdrop-blur-md border-y border-white/10 text-white py-24 px-6 sm:px-8 text-center overflow-hidden">
      <div className="absolute -bottom-32 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full bg-white/[0.05] blur-3xl" />

      <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight relative z-10">
        Ready to plan smarter?
      </h2>

      <p className="mt-3 text-neutral-300 relative z-10">
        Set up your first board in under two minutes.
      </p>

      <Link
        to="/register"
        className="mt-8 inline-block bg-white text-neutral-950 rounded-lg px-6 py-3 text-sm font-medium hover:bg-neutral-200 transition relative z-10 shadow-[0_0_40px_rgba(255,255,255,0.18)]"
      >
        Get started free
      </Link>
    </section>
  );
}

/* =========================================================
   FOOTER
========================================================= */

function Footer() {
  return (
    <footer className="relative px-6 sm:px-8 py-10 border-t border-white/10 bg-black/65 backdrop-blur-md">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <Logo />

        <p className="text-xs text-neutral-400">
          © {new Date().getFullYear()} StackPilot. All rights reserved.
        </p>
      </div>
    </footer>
  );
}

/* =========================================================
   LANDING PAGE
========================================================= */

export default function Landing() {
  return (
    <div className="relative min-h-screen bg-[#020204] text-white">
      <GalaxyBackground />

      <div className="relative z-10">
        <NavBar />
        <Hero />
        <Marquee />
        <Features />
        <HowItWorks />
        <Faq />
        <CtaBanner />
        <Footer />
      </div>
    </div>
  );
}