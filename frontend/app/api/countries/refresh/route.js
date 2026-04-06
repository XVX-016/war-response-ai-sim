import { execSync } from "child_process"
import { join } from "path"

export async function POST() {
  try {
    execSync("python scripts/refresh_world_bank.py", {
      cwd: join(process.cwd(), ".."),
      timeout: 120000,
    })
    return Response.json({ success: true })
  } catch (err) {
    return Response.json({ success: false, error: String(err) }, { status: 500 })
  }
}
