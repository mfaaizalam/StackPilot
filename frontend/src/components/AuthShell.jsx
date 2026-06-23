export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="min-h-screen flex">
      {/* Left brand panel */}
      <div className="hidden lg:flex w-1/2 bg-neutral-950 text-white p-12 flex-col justify-between relative overflow-hidden">
        <div className="flex items-center gap-2 text-lg font-semibold tracking-tight">
          <div className="w-7 h-7 rounded-md bg-white text-neutral-950 flex items-center justify-center font-bold">
            S
          </div>
          StackPilot
        </div>

        <div className="space-y-6 relative z-10">
          <h2 className="text-4xl font-semibold leading-tight tracking-tight">
            Navigate your stack <br /> with precision.
          </h2>
          <p className="text-neutral-400 max-w-md leading-relaxed">
            One calm workspace for the tools, deployments, and decisions that
            keep your product flying.
          </p>
        </div>

        <p className="text-xs text-neutral-500 relative z-10">
          © {new Date().getFullYear()} StackPilot. All rights reserved.
        </p>

        <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-white/5 blur-3xl" />
        <div className="absolute top-1/3 -left-20 w-72 h-72 rounded-full bg-white/5 blur-3xl" />
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12 bg-neutral-50">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-2 mb-10 text-lg font-semibold">
            <div className="w-7 h-7 rounded-md bg-neutral-950 text-white flex items-center justify-center font-bold">
              S
            </div>
            StackPilot
          </div>

          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-neutral-900">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-2 text-sm text-neutral-500">{subtitle}</p>
          )}

          <div className="mt-8">{children}</div>

          {footer && (
            <p className="mt-8 text-sm text-neutral-500 text-center">
              {footer}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
