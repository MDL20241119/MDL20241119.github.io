import type { Metadata } from 'next';
import './globals.css';
export const metadata:Metadata={title:'e-Palette ONE｜今日の運行と準備',description:'次の利用に必要な準備をつなぐ、e-Paletteの共同利用・運行管理アプリ。',icons:{icon:'/favicon.svg',shortcut:'/favicon.svg'}};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="ja"><body>{children}</body></html>}
