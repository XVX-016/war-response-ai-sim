import "leaflet/dist/leaflet.css"
import "./globals.css"
import Providers from "@/components/Providers"

export const metadata = {
  title: "ResilienceSim - Civil Infrastructure Resilience Simulator",
  description:
    "Multi-agent AI simulation of civilian infrastructure resilience. " +
    "Two nations manage cascading failures across power, water, hospitals, " +
    "and transport under crisis conditions.",
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
