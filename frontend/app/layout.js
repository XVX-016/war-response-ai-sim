import "./globals.css"
import { Inter } from "next/font/google"
import Providers from "@/components/Providers"

const inter = Inter({ subsets: ["latin"] })

export const metadata = {
  title: "ResilienceSim — Civil Infrastructure Resilience Simulator",
  description:
    "Multi-agent AI simulation of civilian infrastructure resilience. " +
    "Two nations manage cascading failures across power, water, hospitals, " +
    "and transport under crisis conditions.",
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
