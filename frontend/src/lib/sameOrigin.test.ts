import { describe, expect, it } from 'vitest'
import { API_BASE, stripLoopbackOrigin } from './sameOrigin'

describe('stripLoopbackOrigin', () => {
  it('rewrites loopback :8080 links to site-relative paths', () => {
    expect(stripLoopbackOrigin('http://127.0.0.1:8080/api/news/out/abc')).toBe('/api/news/out/abc')
    expect(stripLoopbackOrigin('http://localhost:8080/news')).toBe('/news')
    expect(stripLoopbackOrigin('https://127.0.0.1:8080')).toBe('')
  })

  it('leaves publisher and production URLs untouched', () => {
    expect(stripLoopbackOrigin('https://example.com/story')).toBe('https://example.com/story')
    expect(stripLoopbackOrigin('/api/news/macro')).toBe('/api/news/macro')
    expect(stripLoopbackOrigin('http://127.0.0.1:11434/v1')).toBe('http://127.0.0.1:11434/v1')
  })
})

describe('API_BASE', () => {
  it('defaults to a relative /api path', () => {
    expect(API_BASE.startsWith('/api') || API_BASE.endsWith('/api')).toBe(true)
    expect(API_BASE).not.toMatch(/127\.0\.0\.1:8080|localhost:8080/)
  })
})
