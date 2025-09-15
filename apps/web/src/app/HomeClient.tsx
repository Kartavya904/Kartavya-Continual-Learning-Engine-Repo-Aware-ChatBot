"use client";
import { useState } from "react";
import AuthModal from "@/components/AuthModal";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const [mode, setMode] = useState<"login" | "signup" | null>(null);
  const router = useRouter();

  return (
    <main className="min-h-screen bg-gradient-to-b from-white to-slate-50">
      <header className="mx-auto max-w-6xl flex items-center justify-between p-6">
        <div className="text-lg font-semibold">Repo-Aware Chat</div>
        <nav className="flex items-center gap-3">
          <button
            className="px-3 py-1.5 rounded border"
            onClick={() => setMode("login")}
          >
            Log in
          </button>
          <button
            className="px-3 py-1.5 rounded bg-black text-white"
            onClick={() => setMode("signup")}
          >
            Sign up
          </button>
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-6 pt-10 pb-24">
        <h1 className="text-5xl font-semibold leading-tight max-w-3xl">
          Repo-aware chat for your monorepo: code-level answers with file:line
          citations.
        </h1>
        <p className="mt-4 text-gray-600 max-w-2xl">
          Connect a repo, index symbols, ask questions, and get grounded answers
          with commit + line ranges. Continual learning keeps results fresh.
        </p>
        <div className="mt-8 flex gap-3">
          <button
            className="px-4 py-2 rounded bg-black text-white"
            onClick={() => setMode("signup")}
          >
            Get started
          </button>
          <a href="/lab" className="px-4 py-2 rounded border">
            Open Lab
          </a>
        </div>
      </section>

      {mode && (
        <AuthModal
          mode={mode}
          onClose={() => setMode(null)}
          onSuccess={() => router.push("/app")}
        />
      )}
    </main>
  );
}
