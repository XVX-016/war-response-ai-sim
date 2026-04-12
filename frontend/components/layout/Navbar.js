"use client"

import { useState } from "react"
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
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0A0A0A]/80 backdrop-blur-sm border-b border-[#1F1F1F]">
        <div className="max-w-7xl mx-auto px-4 md:px-6 h-14 flex items-center justify-between">
          <Link href="/">
            <span className="font-mono text-xs tracking-[0.2em] uppercase text-[#F5F5F5] font-semibold">Resilience-Sim</span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-8">
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

          {/* Mobile hamburger */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden flex flex-col justify-center items-center gap-[5px] w-8 h-8"
            aria-label="Toggle menu"
          >
            <span className={`block w-5 h-[1.5px] bg-[#A3A3A3] transition-all duration-300 ${menuOpen ? "translate-y-[6.5px] rotate-45" : ""}`} />
            <span className={`block w-5 h-[1.5px] bg-[#A3A3A3] transition-all duration-300 ${menuOpen ? "opacity-0" : ""}`} />
            <span className={`block w-5 h-[1.5px] bg-[#A3A3A3] transition-all duration-300 ${menuOpen ? "-translate-y-[6.5px] -rotate-45" : ""}`} />
          </button>
        </div>
      </nav>

      {/* Mobile overlay */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 bg-[#0A0A0A]/95 backdrop-blur-md md:hidden flex flex-col items-center justify-center gap-8 pt-14">
          {LINKS.map(({ href, label }) => (
            <Link key={href} href={href} onClick={() => setMenuOpen(false)}>
              <span
                className={`font-mono text-sm tracking-[0.2em] uppercase transition-colors ${
                  path === href ? "text-[#F5F5F5]" : "text-[#525252]"
                }`}
              >
                {label}
              </span>
              {path === href && (
                <div className="mt-1 h-[1px] w-full bg-[#3B82F6]" />
              )}
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
