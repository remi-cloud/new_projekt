import { useEffect, useId, useRef, type ReactNode } from 'react'
import { useLocale } from '../context/LocaleContext'

interface TagTipProps {
  className?: string
  label: ReactNode
  title: string
  body: string
  hint: string
  openId: string | null
  tipId: string
  onOpen: (id: string | null) => void
}

/** Clickable market tag with a short narrative tooltip (meaning + suggestion). */
export function TagTip({
  className = '',
  label,
  title,
  body,
  hint,
  openId,
  tipId,
  onOpen,
}: TagTipProps) {
  const { t } = useLocale()
  const open = openId === tipId
  const panelId = useId()
  const wrapRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) onOpen(null)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpen(null)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, onOpen])

  return (
    <span className={`tag-tip-wrap${open ? ' is-open' : ''}`} ref={wrapRef}>
      <button
        type="button"
        className={`tag tag-tip-trigger ${className}`.trim()}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={(e) => {
          e.stopPropagation()
          onOpen(open ? null : tipId)
        }}
      >
        {label}
      </button>
      {open && (
        <div
          id={panelId}
          role="dialog"
          className="tag-tip-bubble"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="tag-tip-title">{title}</p>
          <p className="tag-tip-body">
            <span className="tag-tip-kicker">{t('tagTips.meaning')}</span>
            {body}
          </p>
          <p className="tag-tip-hint">
            <span className="tag-tip-kicker">{t('tagTips.suggestion')}</span>
            {hint}
          </p>
          <button type="button" className="tag-tip-close" onClick={() => onOpen(null)}>
            {t('common.close')}
          </button>
        </div>
      )}
    </span>
  )
}
