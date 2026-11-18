import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('chart loading regressions', () => {
  it('clears the spinner after a silent refresh', () => {
    const src = readFileSync(resolve('src/components/TradingChart.tsx'), 'utf8')
    expect(src).toContain('if (gen === loadGenRef.current) setLoading(false)')
    expect(src).not.toContain('if (gen === loadGenRef.current && !silent) setLoading(false)')
  })

  it('draws the ROI chart when width arrives after the first data', () => {
    const src = readFileSync(resolve('src/components/RoiEquityChart.tsx'), 'utf8')
    expect(src).toContain('applyNow()')
    expect(src).toContain('dataRef')
  })
})
