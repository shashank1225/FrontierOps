import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    "https://raw.githubusercontent.com/shashank1225/FrontierOps/main/frontend/public/",
  ),
  title: {
    default: "FrontierOps",
    template: "%s · FrontierOps",
  },
  description: "AI evaluation, deployment, and observability control plane.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  openGraph: {
    title: "FrontierOps · AI Evaluation Control Plane",
    description: "Evaluate, observe, and safely release production LLM applications.",
    images: [{ url: "/og-frontierops.png", width: 1731, height: 909 }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
