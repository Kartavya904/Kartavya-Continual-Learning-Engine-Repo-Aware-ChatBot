// apps/web/src/app/app/github/page.tsx
import GitHubConnectCard from "@/components/GitHubConnectCard";

export default function GitHubLabPage() {
  return (
    <div className="container mx-auto max-w-5xl py-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">GitHub Lab</h1>
        <p className="text-sm text-muted-foreground">
          Browse your repositories and kick off indexing.
        </p>
      </div>

      <GitHubConnectCard />
    </div>
  );
}
