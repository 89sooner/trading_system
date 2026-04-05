export interface PatternBar {
  timestamp: string
  open: string
  high: string
  low: string
  close: string
  volume: string
}

export interface PatternExample {
  label: string
  bars: PatternBar[]
}

export function parseExamples(rawText: string): PatternExample[] {
  const blocks = String(rawText)
    .trim()
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean)

  return blocks.map((block) => {
    const lines = block.split('\n').map((line) => line.trim()).filter(Boolean)
    const [labelLine, ...barLines] = lines
    const label = labelLine.replace(/^label=/i, '').trim()
    return {
      label,
      bars: barLines.map((line) => {
        const [timestamp, open, high, low, close, volume] = line.split(',').map((v) => v.trim())
        return { timestamp, open, high, low, close, volume }
      }),
    }
  })
}
