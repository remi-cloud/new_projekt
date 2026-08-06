import { useState } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice } from '../utils/format'
import { Opportunity } from '../types'
import { useLocale } from '../context/LocaleContext'
import { useDomainLabels } from '../i18n/useDomainLabels'
import { AskAgentButton } from './AskAgentButton'
import { CommunityActions } from './CommunityActions'
import { InstrumentShareMenu } from './InstrumentShareMenu'
import { QuickTradeButtons } from './QuickTradeButtons'
import { TagTip } from './TagTip'
import type { TranslationPath } from '../i18n'

export function OpportunityCard({ opp }: { opp: Opportunity }) {
  const { t } = useLocale()
  const { asset, signal } = useDomainLabels()
  const [openTip, setOpenTip] = useState<string | null>(null)
  const href = `/instrument/${encodeURIComponent(opp.symbol)}`

  return (
    <div className="opp-card card-stretch-host">
      <Link
        to={href}
        className="card-stretch-link"
        aria-label={`${opp.name} ${opp.symbol}`}
      />

      <div className="opp-header">
        <div>
          <div className="opp-name">{opp.name}</div>
          <div className="opp-symbol">{opp.symbol}</div>
        </div>
        <div className="opp-header-actions card-stretch-above">
          <AskAgentButton mode="instrument" symbol={opp.symbol} name={opp.name} compact />
          <CommunityActions
            symbol={opp.symbol}
            name={opp.name}
            community={opp.community}
            compact
          />
          <InstrumentShareMenu
            symbol={opp.symbol}
            name={opp.name}
            kind="instrument"
            signal={signal[opp.action]}
            compact
          />
          <span className={`signal-tag signal-${opp.action}`}>{signal[opp.action]}</span>
        </div>
      </div>

      <div className="price-main-row" style={{ marginBottom: 10 }}>
        <span className="price-live" style={{ fontSize: '1.2rem' }}>
          ${formatPrice(opp.price, opp.asset_class)}
        </span>
      </div>

      <div className="confidence-bar">
        <div className="confidence-track">
          <div className="confidence-fill" style={{ width: `${opp.confidence}%` }} />
        </div>
        <span className="confidence-pct">{opp.confidence}%</span>
      </div>

      <div className="opp-meta market-tags card-stretch-above">
        <TagTip
          tipId="asset"
          openId={openTip}
          onOpen={setOpenTip}
          className={opp.asset_class}
          label={asset[opp.asset_class]}
          title={asset[opp.asset_class]}
          body={t(`tagTips.asset.${opp.asset_class}.body` as TranslationPath)}
          hint={t(`tagTips.asset.${opp.asset_class}.hint` as TranslationPath)}
        />
        <TagTip
          tipId="cycle"
          openId={openTip}
          onOpen={setOpenTip}
          className="region"
          label={opp.cycle_source === 'bitcoin_cycle' ? t('instrument.cycleBtc') : t('instrument.cyclePres')}
          title={opp.cycle_source === 'bitcoin_cycle' ? t('instrument.cycleBtc') : t('instrument.cyclePres')}
          body={t('tagTips.layerCycle.body')}
          hint={t('tagTips.layerCycle.hint')}
        />
        {opp.is_momentum_pick && (
          <TagTip
            tipId="momPick"
            openId={openTip}
            onOpen={setOpenTip}
            className="momentum-pick"
            label={t('opportunities.momentumTag')}
            title={t('opportunities.momentumTag')}
            body={t('tagTips.momPick.body')}
            hint={t('tagTips.momPick.hint')}
          />
        )}
        {opp.momentum_score != null && (
          <TagTip
            tipId="mom"
            openId={openTip}
            onOpen={setOpenTip}
            className="momentum-score"
            label={t('opportunities.momScore', { n: opp.momentum_score.toFixed(0) })}
            title={t('opportunities.momScore', { n: opp.momentum_score.toFixed(0) })}
            body={t('tagTips.momScore.body', { n: opp.momentum_score.toFixed(0) })}
            hint={t('tagTips.momScore.hint')}
          />
        )}
        <TagTip
          tipId="conf"
          openId={openTip}
          onOpen={setOpenTip}
          className={`signal-tag signal-${opp.action}`}
          label={`${opp.confidence}%`}
          title={`${opp.confidence}%`}
          body={t(
            `tagTips.confidence.${opp.confidence >= 80 ? 'high' : opp.confidence >= 60 ? 'mid' : 'low'}.body`,
            { n: opp.confidence },
          )}
          hint={t(
            `tagTips.confidence.${opp.confidence >= 80 ? 'high' : opp.confidence >= 60 ? 'mid' : 'low'}.hint`,
          )}
        />
      </div>
      <p className="opp-rationale">{opp.rationale}</p>
      <div className="card-stretch-above">
        <QuickTradeButtons symbol={opp.symbol} compact />
      </div>
      <span className="tap-hint">{t('opportunities.seeChart')}</span>
    </div>
  )
}
