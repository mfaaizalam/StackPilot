import { Link } from "react-router-dom";
import useReveal from "../hooks/useReveal.js";

function Logo({ dark }) {
  return (
    <Link to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
      <div
        className={
          "w-7 h-7 rounded-md flex items-center justify-center font-bold " +
          (dark ? "bg-white text-neutral-950" : "bg-neutral-950 text-white")
        }
      >
        S
      </div>
      <span className={dark ? "text-white" : "text-neutral-900"}>StackPilot</span>
    </Link>
  );
}

function NavBar() {
  return (
    <header className="absolute top-0 inset-x-0 z-20">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 h-20 flex items-center justify-between">
        <Logo dark />
        <nav className="hidden md:flex items-center gap-8 text-sm text-neutral-300">
          <a href="#features" className="hover:text-white transition">Product</a>
          <a href="#how-it-works" className="hover:text-white transition">How it works</a>
          <a href="#faq" className="hover:text-white transition">FAQ</a>
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

/* Signature hero element: a floating stack of kanban-style cards —
   a literal, board-shaped read of "StackPilot". */
function StackVisual() {
  const columns = [
    { label: "To do", accent: "bg-neutral-700", items: ["Design schema", "Auth flow"] },
    { label: "In progress", accent: "bg-white", items: ["Board API", "AI report"] },
    { label: "Done", accent: "bg-neutral-500", items: ["Project setup"] },
  ];

  return (
    <div className="relative w-full max-w-md mx-auto lg:mx-0 h-[380px]">
      <div className="absolute -bottom-24 -right-16 w-80 h-80 rounded-full bg-white/5 blur-3xl" />
      <div className="absolute -top-16 -left-10 w-64 h-64 rounded-full bg-white/5 blur-3xl" />

      {columns.map((col, i) => (
        <div
          key={col.label}
          className="animate-float absolute w-52 rounded-xl border border-white/10 bg-neutral-900/80 backdrop-blur p-4 shadow-2xl shadow-black/40"
          style={{
            "--tilt": `${(i - 1) * 4}deg`,
            top: `${i * 68}px`,
            left: `${i * 56}px`,
            zIndex: 10 - i,
            animationDelay: `${i * 0.4}s`,
            transform: `rotate(${(i - 1) * 4}deg)`,
          }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-neutral-300">{col.label}</span>
            <span className={`w-2 h-2 rounded-full ${col.accent}`} />
          </div>
          <div className="space-y-2">
            {col.items.map((item) => (
              <div
                key={item}
                className="rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-xs text-neutral-200"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function Hero() {
  return (
    <section className="relative bg-neutral-950 text-white overflow-hidden pt-40 pb-28 px-6 sm:px-8">
      <div className="max-w-6xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
        <div style={{ animation: "fade-in-up 0.8s ease both" }}>
          <span className="inline-flex items-center gap-2 text-xs font-medium tracking-wide text-neutral-300 border border-white/10 rounded-full px-3 py-1 mb-6">
            AI-assisted project management
          </span>
          <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight leading-tight">
            Plan the stack.
            <br />
            Ship the product.
          </h1>
          <p className="mt-5 text-neutral-400 text-lg leading-relaxed max-w-lg">
            Boards, tasks, and an AI that actually reads your project — so you
            spend less time reorganizing tickets and more time building.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-4">
            <Link
              to="/register"
              className="bg-white text-neutral-950 rounded-lg px-5 py-3 text-sm font-medium hover:bg-neutral-200 transition"
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

function Marquee() {
  const stack = ["React", "FastAPI", "PostgreSQL", "Gemini AI", "Qdrant", "Vite"];
  const items = [...stack, ...stack];
  return (
    <section className="bg-neutral-50 border-y border-neutral-100 py-8 overflow-hidden">
      <p className="text-center text-xs uppercase tracking-wide text-neutral-400 mb-5">
        Built on a stack teams already trust
      </p>
      <div className="flex overflow-hidden">
        <div className="marquee-track flex gap-10 pr-10 shrink-0">
          {items.map((name, i) => (
            <span
              key={`${name}-${i}`}
              className="text-neutral-400 font-medium text-sm whitespace-nowrap"
            >
              {name}
            </span>
          ))}
        </div>
        <div className="marquee-track flex gap-10 pr-10 shrink-0" aria-hidden="true">
          {items.map((name, i) => (
            <span
              key={`dup-${name}-${i}`}
              className="text-neutral-400 font-medium text-sm whitespace-nowrap"
            >
              {name}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureCard({ icon, title, desc }) {
  const ref = useReveal();
  return (
    <div ref={ref} className="reveal rounded-2xl border border-neutral-200 p-7">
      <div className="w-10 h-10 rounded-lg bg-neutral-900 text-white flex items-center justify-center mb-5">
        {icon}
      </div>
      <h3 className="font-semibold text-neutral-900 mb-2">{title}</h3>
      <p className="text-sm text-neutral-500 leading-relaxed">{desc}</p>
    </div>
  );
}

function Features() {
  return (
    <section id="features" className="max-w-6xl mx-auto px-6 sm:px-8 py-28">
      <div className="max-w-xl mb-14">
        <h2 className="text-3xl font-semibold tracking-tight text-neutral-900">
          Everything a project needs, nothing it doesn't
        </h2>
        <p className="mt-3 text-neutral-500 leading-relaxed">
          One workspace to organize the work, and an AI layer that understands
          it well enough to help you make decisions.
        </p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        <FeatureCard
          title="Boards & tasks"
          desc="Kanban boards, columns, and tasks that stay out of your way — built for how dev teams actually track work."
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="4" width="6" height="16" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
              <rect x="9.5" y="4" width="6" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
              <rect x="16" y="4" width="5" height="13" rx="1.5" stroke="currentColor" strokeWidth="1.8" />
            </svg>
          }
        />
        <FeatureCard
          title="AI project analysis"
          desc="One click on any board produces a report on feasibility, effort, risk, and where the project stands — not just a task count."
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M4 19V6a1 1 0 0 1 1-1h9l6 6v8a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1Z" stroke="currentColor" strokeWidth="1.8" />
              <path d="M8 13h8M8 16.5h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          }
        />
        <FeatureCard
          title="Ask StackPilot"
          desc="A chat built into every board, so context about your project is always one question away."
          icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M4 5h16v11H8l-4 4V5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
            </svg>
          }
        />
      </div>
    </section>
  );
}

function Step({ n, title, desc }) {
  const ref = useReveal();
  return (
    <div ref={ref} className="reveal flex gap-5">
      <span className="text-sm font-semibold text-neutral-300 tabular-nums pt-1">{n}</span>
      <div>
        <h4 className="font-medium text-neutral-900">{title}</h4>
        <p className="mt-1.5 text-sm text-neutral-500 leading-relaxed max-w-sm">{desc}</p>
      </div>
    </div>
  );
}

function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-neutral-50 border-y border-neutral-100 py-28">
      <div className="max-w-6xl mx-auto px-6 sm:px-8 grid lg:grid-cols-2 gap-16">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-neutral-900">
            From idea to shipped, in order
          </h2>
          <p className="mt-3 text-neutral-500 leading-relaxed max-w-md">
            StackPilot follows the actual life of a project — set it up, break
            it down, then check in on it.
          </p>
        </div>
        <div className="space-y-10">
          <Step n="01" title="Create a board" desc="Spin up a board for your project and lay out the columns that match how your team works." />
          <Step n="02" title="Break it into tasks" desc="Add tasks under each column, assign them, and track them as work moves forward." />
          <Step n="03" title="Ask StackPilot to analyze it" desc="Get a report on where the project stands — feasibility, effort, and what to fix next." />
        </div>
      </div>
    </section>
  );
}

function Faq() {
  const faqs = [
    { q: "Is StackPilot free to use?", a: "You can create an account and start using boards and tasks at no cost while StackPilot is in early access." },
    { q: "What does the AI project analysis look at?", a: "It reads your board's tasks and progress to produce a report on feasibility, effort, and suggestions — not just a status count." },
    { q: "Is the chat assistant available yet?", a: "It's visible in every board and being actively built. You'll see a note if you try a feature that isn't live yet." },
  ];
  return (
    <section id="faq" className="max-w-3xl mx-auto px-6 sm:px-8 py-28">
      <h2 className="text-3xl font-semibold tracking-tight text-neutral-900 mb-10">
        Questions, answered
      </h2>
      <div className="divide-y divide-neutral-200 border-t border-b border-neutral-200">
        {faqs.map((f) => (
          <details key={f.q} className="group py-5">
            <summary className="flex items-center justify-between cursor-pointer list-none text-neutral-900 font-medium">
              {f.q}
              <span className="text-neutral-400 group-open:rotate-45 transition-transform text-xl leading-none">+</span>
            </summary>
            <p className="mt-3 text-sm text-neutral-500 leading-relaxed">{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function CtaBanner() {
  return (
    <section className="bg-neutral-950 text-white py-24 px-6 sm:px-8 text-center relative overflow-hidden">
      <div className="absolute -bottom-32 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full bg-white/5 blur-3xl" />
      <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight relative z-10">
        Ready to plan smarter?
      </h2>
      <p className="mt-3 text-neutral-400 relative z-10">
        Set up your first board in under two minutes.
      </p>
      <Link
        to="/register"
        className="mt-8 inline-block bg-white text-neutral-950 rounded-lg px-6 py-3 text-sm font-medium hover:bg-neutral-200 transition relative z-10"
      >
        Get started free
      </Link>
    </section>
  );
}

function Footer() {
  return (
    <footer className="px-6 sm:px-8 py-10 border-t border-neutral-100">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <Logo />
        <p className="text-xs text-neutral-400">
          © {new Date().getFullYear()} StackPilot. All rights reserved.
        </p>
      </div>
    </footer>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <NavBar />
      <Hero />
      <Marquee />
      <Features />
      <HowItWorks />
      <Faq />
      <CtaBanner />
      <Footer />
    </div>
  );
}
