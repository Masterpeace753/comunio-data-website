import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Shell } from "@/components/layout/Shell";
export const metadata: Metadata = { title: "Comunio Data", description: "Read-only Comunio market intelligence" };
const sans = Inter({ variable: "--font-geist-sans", subsets: ["latin"] });
const mono = JetBrains_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="de" data-theme="dark"><body className={`${sans.variable} ${mono.variable}`}><Shell>{children}</Shell></body></html>; }