// Illustrations bundled with the form: the welcome hero and the photo guides.
// Looked up by file name so the preset can name its guide images; a missing
// file just means no illustration, never a broken build.

const files = import.meta.glob<string>('../assets/illustrations/*.{webp,jpg,png}', {
  eager: true,
  query: '?url',
  import: 'default',
})

const byName = new Map(Object.entries(files).map(([path, url]) => [path.split('/').pop()!, url]))

export function illustration(name: string): string | undefined {
  return byName.get(name)
}

// The hero comes in several widths (hero-car-<width>.webp) for srcset.
const heroes = [...byName.entries()]
  .map(([name, url]) => ({ width: Number(/^hero-car-(\d+)\.webp$/.exec(name)?.[1]), url }))
  .filter((hero) => hero.width)
  .sort((a, b) => a.width - b.width)

// The designs' car is a 3:2 photo (hero-car-1536.webp is 1536x1024).
export const hero = heroes.length
  ? { src: heroes.at(-1)!.url, srcset: heroes.map((h) => `${h.url} ${h.width}w`).join(', '), ratio: 3 / 2 }
  : undefined
