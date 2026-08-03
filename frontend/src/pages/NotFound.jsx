import { Link } from "react-router-dom";

function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
      <div className="w-7 h-7 rounded-md flex items-center justify-center font-bold bg-white text-neutral-950">
        S
      </div>
      <span className="text-white">StackPilot</span>
    </Link>
  );
}

export default function NotFound() {
  return (
    <div className="min-h-screen bg-neutral-950 text-white flex flex-col relative overflow-hidden">
      {/* Ambient glow, consistent with Hero/CTA sections */}
      <div className="absolute -top-32 -left-24 w-96 h-96 rounded-full bg-white/5 blur-3xl" />
      <div className="absolute -bottom-32 -right-24 w-96 h-96 rounded-full bg-white/5 blur-3xl" />

      <header className="relative z-10 px-6 sm:px-8 h-20 flex items-center">
        <Logo />
      </header>

      <main className="relative z-10 flex-1 flex items-center justify-center px-6 sm:px-8 text-center">
        <div style={{ animation: "fade-in-up 0.8s ease both" }}>
          <span className="inline-flex items-center gap-2 text-xs font-medium tracking-wide text-neutral-300 border border-white/10 rounded-full px-3 py-1 mb-6">
            Error 404
          </span>

          <h1 className="text-6xl sm:text-8xl font-semibold tracking-tight leading-none">
            404
          </h1>

          <h2 className="mt-4 text-2xl sm:text-3xl font-semibold tracking-tight">
            This page went off-board.
          </h2>

          <p className="mt-4 text-neutral-400 text-lg leading-relaxed max-w-md mx-auto">
            The page you're looking for doesn't exist, was moved, or the
            link is broken. Let's get you back on track.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/"
              className="bg-white text-neutral-950 rounded-lg px-5 py-3 text-sm font-medium hover:bg-neutral-200 transition"
            >
              Back to home
            </Link>
            <Link
              to="/login"
              className="text-sm font-medium text-neutral-300 hover:text-white transition"
            >
              Sign in →
            </Link>
          </div>
        </div>
      </main>

      <footer className="relative z-10 px-6 sm:px-8 py-8 text-center">
        <p className="text-xs text-neutral-500">
          © {new Date().getFullYear()} StackPilot. All rights reserved.
        </p>
      </footer>
    </div>
  );
}