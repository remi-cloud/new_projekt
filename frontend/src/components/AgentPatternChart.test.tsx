import { describe, expect, it } from 'vitest'
import { sanitizeSvg } from './AgentPatternChart'

describe('pattern chart svg', () => {
  it('keeps a server chart and drops script or handlers', () => {
    const chart = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'
    expect(sanitizeSvg(chart)).toBe(chart)
    expect(sanitizeSvg('<svg><script>alert(1)</script></svg>')).toBe('')
    expect(sanitizeSvg('<svg><rect onload="alert(1)"/></svg>')).toBe('')
    expect(sanitizeSvg('<svg><foreignObject></foreignObject></svg>')).toBe('')
  })
})