import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "大分未来モビリティコンソーシアム｜タスク管理",
  description: "コンソーシアムの立上げに向けたタスク、工程、判断事項を共同管理。",
  robots: { index: false, follow: false },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className="antialiased">{children}</body>
    </html>
  );
}
