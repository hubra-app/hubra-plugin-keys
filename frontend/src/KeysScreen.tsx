import { useState } from 'react'
import { Button, Menu, ActionIcon } from '@mantine/core'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { IconDots, IconPlus } from '@tabler/icons-react'
import { ConfirmModal, DataTable, Modal, PageHead, useAuth, useNav, useT, useToast } from '@hubra/plugin-sdk'
import {
  deleteKey,
  getKey,
  keyAction,
  listKeys,
  type ClubKey,
  type KeyAction,
  type KeyStatus,
} from './api'
import { IssueModal, KeyFormModal, KeyHistory, STATUS_COLORS } from './KeyModals'

export function KeysScreen() {
  const { t } = useT()
  const { notify } = useToast()
  const { hasPermission } = useAuth()
  const { go } = useNav()
  const queryClient = useQueryClient()
  const canManage = hasPermission('keys.keys.manage')

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ['keys'],
    queryFn: listKeys,
  })
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<KeyStatus | 'all'>('all')
  const [editing, setEditing] = useState<ClubKey | 'new' | null>(null)
  const [issuing, setIssuing] = useState<ClubKey | null>(null)
  const [deleting, setDeleting] = useState<ClubKey | null>(null)
  const [historyId, setHistoryId] = useState<number | null>(null)

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['keys'] })

  const fail = (err: unknown) =>
    notify(
      'error',
      t('common.error'),
      err instanceof Error ? err.message : t('common.unknownError'),
    )

  const openEdit = (k: ClubKey | 'new') => setEditing(k)

  const run = async (k: ClubKey, action: KeyAction) => {
    try {
      await keyAction(k.id, action)
      await refresh()
    } catch (err) {
      fail(err)
    }
  }

  const remove = async () => {
    if (!deleting) return
    try {
      await deleteKey(deleting.id)
      await refresh()
      setDeleting(null)
    } catch (err) {
      fail(err)
    }
  }

  const filtered = keys.filter((k) => {
    const q = search.toLowerCase()
    const matches =
      !q ||
      [k.label, k.number, k.opens, k.holderName].some((v) => (v ?? '').toLowerCase().includes(q))
    return matches && (statusFilter === 'all' || k.status === statusFilter)
  })

  const statusLabel = (s: KeyStatus) => t(`keys.status.${s}`, s)

  return (
    <div>
      <PageHead
        title={t('keys.title', 'Keys')}
        desc={t('keys.count', '{{count}} keys', { count: filtered.length })}
        actions={
          canManage ? (
            <Button variant="default" onClick={() => openEdit('new')}>
              <IconPlus size={16} />
              {t('keys.add', 'Add key')}
            </Button>
          ) : undefined
        }
      />

      <DataTable
        breakpoint="wide"
        data={filtered}
        loading={isLoading}
        emptyMessage={t('keys.empty', 'No keys yet.')}
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder={t('keys.search', 'Search label, number, holder…')}
        // A key is an inventory item: its page there has the details,
        // the handover buttons and the history.
        onRowClick={(k) => (k.itemId ? go(`/app/inventory/${k.itemId}`) : setHistoryId(k.id))}
        getRowKey={(k) => k.id}
        filters={(['all', 'available', 'issued', 'lost'] as const).map((s) => ({
          label: s === 'all' ? t('common.all', 'All') : statusLabel(s),
          value: s,
          active: statusFilter === s,
          onClick: () => setStatusFilter(s),
        }))}
        columns={[
          {
            key: 'label',
            header: t('keys.label', 'Label'),
            render: (k) => (
              <span>
                <strong>{k.label}</strong>
                {k.number && (
                  <span className="num" style={{ color: '#6b7480', marginLeft: 8 }}>
                    {k.number}
                  </span>
                )}
              </span>
            ),
          },
          {
            key: 'kind',
            header: t('keys.kind', 'Type'),
            render: (k) => t(`keys.kinds.${k.kind}`, k.kind),
          },
          {
            key: 'opens',
            header: t('keys.opens', 'Opens'),
            render: (k) => <span style={{ color: '#6b7480' }}>{k.opens ?? '—'}</span>,
          },
          {
            key: 'status',
            header: t('keys.statusLabel', 'Status'),
            render: (k) => (
              <span
                className="chip"
                style={{
                  fontSize: 'var(--mantine-font-size-xs)',
                  color: STATUS_COLORS[k.status],
                }}
              >
                {statusLabel(k.status)}
              </span>
            ),
          },
          {
            key: 'holder',
            header: t('keys.holder', 'Holder'),
            render: (k) => k.holderName ?? '—',
          },
          {
            key: 'deposit',
            header: t('keys.deposit', 'Deposit'),
            render: (k) => (k.depositChf ? <span className="num">CHF {k.depositChf}</span> : '—'),
          },
          {
            key: 'actions',
            header: t('common.actions'),
            width: 60,
            render: (k) =>
              canManage ? (
                <Menu position="bottom-end" withinPortal>
                  <Menu.Target>
                    <ActionIcon
                      variant="subtle"
                      aria-label={t('common.actions')}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <IconDots size={16} />
                    </ActionIcon>
                  </Menu.Target>
                  <Menu.Dropdown onClick={(e) => e.stopPropagation()}>
                    {k.status === 'available' && (
                      <Menu.Item onClick={() => setIssuing(k)}>
                        {t('keys.issue', 'Hand out')}
                      </Menu.Item>
                    )}
                    {k.status === 'issued' && (
                      <Menu.Item onClick={() => run(k, 'return')}>
                        {t('keys.return', 'Take back')}
                      </Menu.Item>
                    )}
                    {(k.status === 'available' || k.status === 'issued') && (
                      <Menu.Item onClick={() => run(k, 'lost')}>
                        {t('keys.markLost', 'Mark as lost')}
                      </Menu.Item>
                    )}
                    {k.status === 'lost' && (
                      <Menu.Item onClick={() => run(k, 'found')}>
                        {t('keys.markFound', 'Found again')}
                      </Menu.Item>
                    )}
                    {k.status !== 'retired' && k.status !== 'issued' && (
                      <Menu.Item onClick={() => run(k, 'retire')}>
                        {t('keys.retire', 'Retire')}
                      </Menu.Item>
                    )}
                    <Menu.Item onClick={() => openEdit(k)}>{t('common.edit', 'Edit')}</Menu.Item>
                    {k.status !== 'issued' && (
                      <Menu.Item color="red" onClick={() => setDeleting(k)}>
                        {t('common.delete', 'Delete')}
                      </Menu.Item>
                    )}
                  </Menu.Dropdown>
                </Menu>
              ) : null,
          },
        ]}
      />

      {editing && (
        <KeyFormModal
          clubKey={editing}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            await refresh()
            setEditing(null)
            notify('success', t('keys.saved', 'Key saved'))
          }}
          onError={fail}
        />
      )}

      {issuing && (
        <IssueModal
          clubKey={issuing}
          onClose={() => setIssuing(null)}
          onDone={async () => {
            await refresh()
            setIssuing(null)
          }}
          onError={fail}
        />
      )}

      {historyId !== null && <HistoryModal keyId={historyId} onClose={() => setHistoryId(null)} />}

      <ConfirmModal
        open={!!deleting}
        title={t('keys.delete', 'Delete key')}
        body={
          deleting
            ? t('keys.deleteConfirm', 'Delete {{name}} and its history?', {
                name: deleting.label,
              })
            : undefined
        }
        onConfirm={remove}
        onClose={() => setDeleting(null)}
      />
    </div>
  )
}

function HistoryModal({ keyId, onClose }: { keyId: number; onClose: () => void }) {
  const { t } = useT()
  const { data: key } = useQuery({
    queryKey: ['keys', keyId],
    queryFn: () => getKey(keyId),
  })
  return (
    <Modal
      open
      onClose={onClose}
      title={key?.label ?? t('keys.title', 'Keys')}
      subtitle={key?.opens ?? undefined}
    >
      {key?.notes && <p style={{ marginTop: 0, color: '#6b7480' }}>{key.notes}</p>}
      <KeyHistory history={key?.history ?? []} />
    </Modal>
  )
}
