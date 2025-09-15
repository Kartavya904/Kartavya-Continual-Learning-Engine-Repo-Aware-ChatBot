import { redirect } from "next/navigation";
import { getUserServer } from "@/lib/session";
import HomeClient from "./HomeClient"; // reuse your existing client file; or rename it

export default async function Home() {
  const user = await getUserServer();
  if (user) redirect("/app");
  return <HomeClient />; // your existing hero with AuthModal
}
