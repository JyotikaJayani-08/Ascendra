import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Ascendra | AI Career Platform",
  description: "Reverse headhunting with AI-optimized resumes and automated outreach.",
};

import { AuthProvider } from '@/contexts/AuthContext';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased min-h-screen bg-app-gradient animated-bg`}>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
