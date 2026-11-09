import { useState } from 'react'
import { Button, Group, SimpleGrid } from '@mantine/core'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { PanelField, PanelSection, useAuth, useT, useToast } from '@hubra/plugin-sdk'
import { getKeyByItem, keyAction, revealCode, type ClubKey, type KeyAction } from './api'
import { IssueModal, KeyFormModal, STATUS_COLORS } from './KeyModals'

/**
 * On the inventory page of an item of the type "Key": what only a key has
 * (kind, what it opens, deposit), who holds it and the handover buttons.
 * The handovers are in the item's history in Inventory. Shows nothing for
 * any other item.
 */
export function KeyItemPanel({ itemId }: { itemId: number }) {
  const { t } = useT()
  const { notify } = useToast()
  const { hasPermission } = useAuth()
  const queryClient = useQueryClient()
  const canManage = hasPermission('keys.keys.manage')
  const [editing, setEditing] = useState(false)
  const [issuing, setIssuing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [shown, setShown] = useState<string | null>(null)

  const { data: key } = useQuery({
    queryKey: ['keys', 'item', itemId],
    queryFn: () => getKeyByItem(itemId),
    retry: false,
  })
  if (!key) return null

  // The item's status and name follow the key, so the page above reloads too.
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['keys'] }),
      queryClient.invalidateQueries({ queryKey: ['inventory'] }),
    ])
  const fail = (err: unknown) =>
    notify('error', t('common.error'), err instanceof Error ? err.message : t('common.unknownError'))

  const run = async (k: ClubKey, action: KeyAction) => {
    setBusy(true)
    try {
      await keyAction(k.id, action)
      await refresh()
    } catch (err) {
      fail(err)
    } finally {
      setBusy(false)
    }
  }

  const statusLabel = t(`keys.status.${key.status}`, key.status)
  const isCode = key.kind === 'code'
  const assigned = [
    ...(key.members ?? []).map((m) => m.name ?? ''),
    ...(key.groups ?? []).map((g) => g.name ?? ''),
  ].filter(Boolean)
  const access = key.public
    ? t('keys.publicShort', 'Every member')
    : assigned.length
      ? assigned.join(', ')
      : t('keys.nobodyAssigned', 'Nobody assigned')
  const show = async () => {
    try {
      setShown((await revealCode(key.id)).code ?? '')
    } catch (err) {
      fail(err)
    }
  }

  return (
    <>
      <PanelSection
        label={t('keys.panel', 'Key')}
        right={
          canManage ? (
            <Button size="compact-xs" variant="subtle" onClick={() => setEditing(true)}>
              {t('common.edit', 'Edit')}
            </Button>
          ) : undefined
        }
      >
        <SimpleGrid cols={2} spacing={12} verticalSpacing={10}>
          <PanelField label={t('keys.statusLabel', 'Status')}>
            <span style={{ color: STATUS_COLORS[key.status], fontWeight: 600 }}>{statusLabel}</span>
          </PanelField>
          {isCode ? (
            <PanelField label={t('keys.code', 'Code')}>
              {shown !== null ? (
                <span className="num">{shown || '—'}</span>
              ) : key.hasCode ? (
                <Button size="compact-xs" variant="subtle" onClick={show}>
                  {t('keys.showCode', 'Show')}
                </Button>
              ) : (
                '—'
              )}
            </PanelField>
          ) : (
            <PanelField label={t('keys.holder', 'Holder')}>{key.holderName ?? '—'}</PanelField>
          )}
          <PanelField label={t('keys.kind', 'Type')}>{t(`keys.kinds.${key.kind}`, key.kind)}</PanelField>
          <PanelField label={t('keys.number', 'Number')}>
            <span className="num">{key.number ?? '—'}</span>
          </PanelField>
          <PanelField label={t('keys.opens', 'Opens')}>{key.opens ?? '—'}</PanelField>
          <PanelField label={t('keys.access', 'Who may use it')}>{access}</PanelField>
          <PanelField label={t('keys.deposit', 'Deposit')}>
            {key.depositChf ? <span className="num">CHF {key.depositChf}</span> : '—'}
          </PanelField>
        </SimpleGrid>
        {key.notes && canManage && (
          <p style={{ margin: '12px 0 0', color: 'var(--hb-text-3)', fontSize: 'var(--mantine-font-size-sm)' }}>
            {key.notes}
          </p>
        )}
        {canManage && (
          <Group gap={8} mt="md">
            {key.status === 'available' && !isCode && (
              <Button size="sm" onClick={() => setIssuing(true)} disabled={busy}>
                {t('keys.issue', 'Hand out')}
              </Button>
            )}
            {key.status === 'issued' && (
              <Button size="sm" onClick={() => run(key, 'return')} disabled={busy}>
                {t('keys.return', 'Take back')}
              </Button>
            )}
            {(key.status === 'available' || key.status === 'issued') && !isCode && (
              <Button size="sm" variant="default" onClick={() => run(key, 'lost')} disabled={busy}>
                {t('keys.markLost', 'Mark as lost')}
              </Button>
            )}
            {key.status === 'lost' && (
              <Button size="sm" variant="default" onClick={() => run(key, 'found')} disabled={busy}>
                {t('keys.markFound', 'Found again')}
              </Button>
            )}
            {key.status !== 'retired' && key.status !== 'issued' && (
              <Button size="sm" variant="subtle" onClick={() => run(key, 'retire')} disabled={busy}>
                {t('keys.retire', 'Retire')}
              </Button>
            )}
          </Group>
        )}
      </PanelSection>

      {editing && (
        <KeyFormModal
          clubKey={key}
          onClose={() => setEditing(false)}
          onSaved={async () => {
            await refresh()
            setEditing(false)
            notify('success', t('keys.saved', 'Key saved'))
          }}
          onError={fail}
        />
      )}
      {issuing && (
        <IssueModal
          clubKey={key}
          onClose={() => setIssuing(false)}
          onDone={async () => {
            await refresh()
            setIssuing(false)
          }}
          onError={fail}
        />
      )}
    </>
  )
}
