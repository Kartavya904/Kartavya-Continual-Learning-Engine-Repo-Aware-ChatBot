"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

type User = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
};

export default function AppHome() {
  const [user, setUser] = useState<User | null>(null);
  const [ghConnected, setGhConnected] = useState(false);
  const router = useRouter();

  useEffect(() => {
    (async () => {
      const me = await fetch("/api/me");
      if (!me.ok) {
        router.push("/");
        return;
      }
      setUser(await me.json());
      const gh = await fetch("/api/github/status", { cache: "no-store" });
      setGhConnected(gh.ok);
    })();
  }, [router]);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/");
  }

  return (
    <main className="min-h-screen">
      <header className="mx-auto max-w-6xl flex items-center justify-between p-4 border-b">
        <div className="font-medium">Repo-Aware Chat</div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">
            {user ? `${user.first_name} ${user.last_name}` : ""}
          </span>
          {ghConnected && (
            <Link
              href="/app/github"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              GitHub Lab
            </Link>
          )}
          <Link
            href="/app/settings"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Settings
          </Link>
          <div className="relative">
            <details>
              <summary className="cursor-pointer rounded border px-3 py-1 text-sm">
                Profile ▾
              </summary>
              <div className="absolute right-0 mt-1 w-40 rounded border bg-white shadow">
                <a
                  className="block px-3 py-2 text-sm hover:bg-gray-50"
                  href="/app"
                >
                  Home
                </a>
                <a
                  className="block px-3 py-2 text-sm hover:bg-gray-50"
                  href="/lab"
                >
                  Lab
                </a>
                <button
                  className="block w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                  onClick={logout}
                >
                  Log out
                </button>
              </div>
            </details>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-4xl p-6">
        <div className="rounded-2xl border p-4">
          <div className="text-sm text-gray-500 mb-2">Chat (stub)</div>
          <div className="flex gap-2">
            <input
              className="flex-1 border rounded px-3 py-2"
              placeholder="Ask about your repo…"
            />
            <button className="border rounded px-4 py-2 bg-black text-white">
              Send
            </button>
          </div>
          <p className="mt-4 text-gray-500 text-sm">
            We&apos;ll wire this to your Brain chat shortly.
          </p>
        </div>
      </section>
    </main>
  );
}
