// apps/web/src/components/GitHubConnectCard.tsx
"use client";

import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, Github } from "lucide-react";

type Status = { connected: boolean; username?: string | null };

export default function GitHubConnectCard() {
  const [loading, setLoading] = React.useState(true);
  const [connecting, setConnecting] = React.useState(false);
  const [status, setStatus] = React.useState<Status>({ connected: false });

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/github/status", { cache: "no-store" });
        const json = (await res.json()) as Status;
        if (!cancelled) setStatus(json);
      } catch {
        // keep default disconnected
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const onConnect = async () => {
    setConnecting(true);
    try {
      const res = await fetch("/api/github/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ next: "/app/github" }),
      });
      const json = (await res.json()) as { url: string; next?: string };
      // For now this is a placeholder; swap with real GitHub App installation URL later.
      if (json?.url) {
        // Prefer opening in same tab to keep auth cookie scope simple.
        window.location.href = json.url;
        return;
      }
      alert("GitHub installation flow coming soon.");
    } catch {
      alert("Failed to start GitHub connect. Try again.");
    } finally {
      setConnecting(false);
    }
  };

  const onDisconnect = async () => {
    alert("Disconnect coming soon.");
  };

  return (
    <Card className="border-dashed">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle>GitHub</CardTitle>
          <CardDescription>
            Connect your GitHub account to index repos and enable repo-aware
            chat.
          </CardDescription>
        </div>
        {loading ? (
          <Badge variant="secondary" className="gap-1">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Checking…
          </Badge>
        ) : status.connected ? (
          <Badge className="bg-green-600 hover:bg-green-600">Connected</Badge>
        ) : (
          <Badge variant="outline">Not connected</Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-sm text-muted-foreground">
          {status.connected
            ? `Signed in as ${
                status.username ?? "unknown"
              }. You can manage installations and choose which repos to index.`
            : "You’ll be redirected to GitHub to approve access. We only request the minimum needed to list repositories and receive webhooks."}
        </p>
      </CardContent>
      <CardFooter className="flex items-center gap-2">
        {status.connected ? (
          <Button
            variant="outline"
            onClick={onDisconnect}
            disabled={connecting}
          >
            Disconnect
          </Button>
        ) : (
          <Button onClick={onConnect} disabled={connecting}>
            {connecting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Github className="mr-2 h-4 w-4" />
            )}
            Connect GitHub
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
