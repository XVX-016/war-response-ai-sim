"use client"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { useSimStore } from "@/store/simStore"

export default function Providers({ children }) {
  const [queryClient] = useState(
    () => new QueryClient({
      defaultOptions: {
        queries: { staleTime: 0, retry: 1 },
      },
    })
  )
  useEffect(() => {
    fetch("/api/countries")
      .then((r) => r.json())
      .then((data) => {
        useSimStore.getState().setCountryCache(data.countries || {})
      })
      .catch(() => {})
  }, [])
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
