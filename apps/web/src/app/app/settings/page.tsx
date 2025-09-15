// apps/web/src/app/app/settings/page.tsx
import { Suspense } from "react";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import GitHubConnectCard from "@/components/GitHubConnectCard";

export default function SettingsPage() {
  return (
    <div className="container mx-auto max-w-5xl py-8 space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your account, security, and integrations.
        </p>
      </div>
      <Separator />
      <Tabs defaultValue="integrations" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="account">
          <Card>
            <CardHeader>
              <CardTitle>Account</CardTitle>
              <CardDescription>
                Profile, email, and basic preferences.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Placeholder for now.
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Security</CardTitle>
              <CardDescription>Password and sessions.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Placeholder for now.
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="integrations">
          <div className="grid gap-6 md:grid-cols-2">
            <Suspense
              fallback={
                <div className="text-sm text-muted-foreground">Loading…</div>
              }
            >
              <GitHubConnectCard />
            </Suspense>
          </div>
        </TabsContent>

        <TabsContent value="advanced">
          <Card>
            <CardHeader>
              <CardTitle>Advanced</CardTitle>
              <CardDescription>Experimental toggles & budgets.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Placeholder for now.
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
