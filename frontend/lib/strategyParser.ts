export function parseMap(rawText: string): Record<string, string>
export function parseMap(rawText: string, parser: (v: string) => number): Record<string, number>
export function parseMap(
  rawText: string,
  parser?: (v: string) => string | number,
): Record<string, string | number> {
  const entries = String(rawText)
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.split('=').map((v) => v.trim()))
  return Object.fromEntries(
    entries.map(([key, value]) => [key, parser ? parser(value) : value]),
  )
}
