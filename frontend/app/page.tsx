import type { Metadata } from "next";
import { Dashboard } from "@/components/dashboard";

export const metadata: Metadata = {
  title: "Overview",
  description: "Monitor AI application quality, latency, cost, and release readiness.",
};

export default function Home() {
  return <Dashboard />;
}
