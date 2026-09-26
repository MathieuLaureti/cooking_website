/** Write solid brand-color PNGs for the web app manifest (no external image deps). */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { PNG } from 'pngjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const publicDir = path.join(__dirname, '..', 'public')

function writeIcon(size, filename) {
  const png = new PNG({ width: size, height: size })
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (size * y + x) << 2
      png.data[idx] = 0x4a
      png.data[idx + 1] = 0x59
      png.data[idx + 2] = 0x4d
      png.data[idx + 3] = 255
    }
  }
  fs.mkdirSync(publicDir, { recursive: true })
  fs.writeFileSync(path.join(publicDir, filename), PNG.sync.write(png))
}

writeIcon(192, 'pwa-192x192.png')
writeIcon(512, 'pwa-512x512.png')
writeIcon(180, 'apple-touch-icon.png')
