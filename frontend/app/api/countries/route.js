import { readFileSync } from "fs"
import { join } from "path"

export async function GET() {
  try {
    const cachePath = join(process.cwd(), "..", "data", "countries", "world_bank_cache.json")
    const raw = readFileSync(cachePath, "utf-8")
    const data = JSON.parse(raw)
    return Response.json(data, {
      headers: {
        "Cache-Control": "public, max-age=3600",
      },
    })
  } catch (err) {
    return Response.json({ countries: {}, error: String(err) }, { status: 500 })
  }
}
