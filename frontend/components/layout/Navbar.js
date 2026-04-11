"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/setup", label: "Setup" },
  { href: "/sim", label: "Simulation" },
  { href: "/vision", label: "Vision" },
]

export default function Navbar() {
  const path = usePathname()
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A0A]/80 backdrop-blur-sm border-b border-[#1F1F1F]">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/">
          <span className="font-mono text-xs tracking-[0.2em] uppercase text-[#F5F5F5] font-semibold">Resilience-Sim</span>
        </Link>
        <div className="flex items-center gap-8">
          {LINKS.map(({ href, label }) => (
            <Link key={href} href={href}>
              <span
                className={`font-mono text-xs tracking-[0.15em] uppercase transition-colors ${
                  path === href
                    ? "text-[#F5F5F5] border-b border-[#3B82F6] pb-0.5"
                    : "text-[#525252] hover:text-[#A3A3A3]"
                }`}
              >
                {label}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}
