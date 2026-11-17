/**
 * Public warning published by remi-cloud/radar (branch arch-clean, public/index.html).
 * Identifiers only — no live links to the reported accounts.
 * Scores are the tool's automated estimate from 2026-11-10, not a legal finding.
 */

export type RadarNode = {
  id: number
  kind: string
  label: string
  net: 'S1' | 'S2'
  score: number
  x: number
  y: number
}

export const RADAR_EDGES: [number, number][] = [
  [1, 2],
  [1, 3],
  [1, 4],
  [1, 5],
  [1, 6],
  [3, 6],
  [7, 8],
  [7, 9],
  [9, 10],
  [9, 11],
  [9, 12],
]

export const RADAR_NODES: RadarNode[] = [
  { id: 1, kind: 'konto', label: '@E___m2677', net: 'S1', score: 100, x: 150, y: 70 },
  { id: 2, kind: 'xid', label: '1290490287345643522', net: 'S1', score: 100, x: 40, y: 150 },
  { id: 3, kind: 'tel', label: '+1 541 452 0848', net: 'S1', score: 100, x: 150, y: 230 },
  { id: 4, kind: 'tg', label: 'XXXXX029ELON', net: 'S1', score: 100, x: 280, y: 150 },
  { id: 5, kind: 'nick', label: 'Elon101020', net: 'S1', score: 100, x: 260, y: 50 },
  { id: 6, kind: 'zangi', label: 'Zangi', net: 'S1', score: 100, x: 40, y: 50 },
  { id: 7, kind: 'konto', label: '@VitoNakamoto', net: 'S2', score: 85, x: 520, y: 70 },
  { id: 8, kind: 'xid', label: '1742919732972728321', net: 'S2', score: 85, x: 400, y: 150 },
  { id: 9, kind: 'sol', label: 'Bsbs…pump', net: 'S2', score: 85, x: 520, y: 230 },
  { id: 10, kind: 'ticker', label: '$GTA', net: 'S2', score: 85, x: 660, y: 150 },
  { id: 11, kind: 'konto', label: '@GTAmemesSOL', net: 'S2', score: 85, x: 560, y: 36 },
  { id: 12, kind: 'tg', label: 'GTAbagwork', net: 'S2', score: 85, x: 400, y: 50 },
]

export const RADAR_KIND_COLOR: Record<string, string> = {
  konto: '#e74c3c',
  xid: '#95a5a6',
  tel: '#f39c12',
  tg: '#3498db',
  nick: '#e67e22',
  zangi: '#1abc9c',
  sol: '#9b59b6',
  ticker: '#e67e22',
}

export const RADAR_SOURCE = 'https://github.com/remi-cloud/radar'
export const RADAR_PUBLISHED = '2026-11-10T12:35:36Z'
