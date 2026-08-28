import type { Metadata, Viewport } from "next";
import { Toaster } from "sonner";
import "./globals.css";
import { ThemeScript } from "@/components/theme-script";
import { TopNav } from "@/components/top-nav";

export const metadata: Metadata = {
  title: "ChatGPT 号池管理",
  description: "ChatGPT account pool management dashboard",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f4f7" },
    { media: "(prefers-color-scheme: dark)", color: "#111315" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body
        className="antialiased"
        style={{
          fontFamily:
            '"SF Pro Display","SF Pro Text","PingFang SC","Microsoft YaHei","Helvetica Neue",sans-serif',
        }}
      >
        <Toaster position="top-center" richColors offset={48} />
        <main className="min-h-dvh overflow-x-hidden bg-[#f2f4f7] px-4 pt-0 pb-2 text-stone-900 dark:bg-[#111315] dark:text-stone-100 sm:px-6 sm:pt-2 lg:px-8">
          <div className="mx-auto box-border flex min-h-dvh max-w-[1440px] flex-col gap-2 pt-[env(safe-area-inset-top)] sm:gap-5 sm:pt-0">
            <TopNav />
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
