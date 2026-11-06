import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Badge, Button, Group, Modal, NumberInput, Paper, Select, Stack, Switch, Text, TextInput } from '@mantine/core'
import { IconLock, IconPlus, IconRefresh } from '@tabler/icons-react'
import { ConfirmModal, EmptyState, ErrorBanner, LoadingSpinner, PageHead, formatDateTime, useT, useToast } from '@hubra/plugin-sdk'
import { createLock, deleteLock, listLocks, syncLock, updateLock, type LockInput, type SmartLock } from './api'

const KEY = ['keys', 'locks']
const STATUS_COLOR = { active: 'green', pending: 'gray', failed: 'red' } as const

/** Nuki smart locks: who may open them follows membership and groups. */
export function LocksScreen() {
  const { t } = useT()
  const { notify } = useToast()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: KEY, queryFn: listLocks })
  const [editing, setEditing] = useState<SmartLock | 'new' | null>(null)
  const [busy, setBusy] = useState<number | null>(null)

  if (q.error) return <ErrorBanner message={String((q.error as Error).message)} onRetry={() => q.refetch()} />
  if (q.isLoading || !q.data) return <LoadingSpinner />
  const { locks, groups, configured } = q.data
  const groupName = (id: number | null) => (id ? (groups.find((g) => g.id === id)?.name ?? '') : t('locks.everyone'))

  const report = (lock: SmartLock) => {
    const s = lock.sync
    if (!s) return
    if (s.failed) notify('error', t('locks.syncFailed', { count: s.failed }))
    else notify('success', t('locks.synced', { added: s.added, removed: s.removed }))
  }

  const sync = async (lock: SmartLock) => {
    setBusy(lock.id)
    try {
      report(await syncLock(lock.id))
    } catch (err) {
      notify('error', err instanceof Error ? err.message : String(err))
    }
    setBusy(null)
    qc.invalidateQueries({ queryKey: KEY })
  }

  return (
    <>
      <PageHead
        title={t('locks.title')}
        desc={t('locks.desc')}
        actions={
          <Button leftSection={<IconPlus size={16} />} onClick={() => setEditing('new')}>
            {t('locks.add')}
          </Button>
        }
      />
      {!configured && (
        <Alert color="yellow" mb="md">
          {t('locks.noToken')}
        </Alert>
      )}
      {!locks.length ? (
        <EmptyState icon={<IconLock size={28} />} title={t('locks.none')} description={t('locks.noneHint')} />
      ) : (
        <Stack gap="md">
          {locks.map((lock) => {
            const failed = (lock.access ?? []).filter((a) => a.status === 'failed')
            return (
              <Paper key={lock.id} withBorder radius="md" p="md">
                <Group justify="space-between" wrap="nowrap" align="flex-start">
                  <div style={{ minWidth: 0 }}>
                    <Text fw={700}>{lock.name}</Text>
                    <Text fz="sm" c="dimmed">
                      {t('locks.who', { group: groupName(lock.groupId), count: lock.access?.length ?? 0 })}
                      {' · '}
                      {[lock.keypad && t('locks.keypad'), lock.appOpen && t('locks.appOpen')].filter(Boolean).join(', ') || t('locks.off')}
                    </Text>
                    <Text fz="xs" c="dimmed">
                      {lock.syncedAt ? t('locks.syncedAt', { when: formatDateTime(lock.syncedAt) }) : t('locks.notSynced')}
                    </Text>
                  </div>
                  <Group gap="xs" wrap="nowrap">
                    <Button size="xs" variant="default" leftSection={<IconRefresh size={14} />} loading={busy === lock.id} onClick={() => sync(lock)}>
                      {t('locks.sync')}
                    </Button>
                    <Button size="xs" variant="subtle" onClick={() => setEditing(lock)}>
                      {t('locks.edit')}
                    </Button>
                  </Group>
                </Group>
                {failed.length > 0 && (
                  <Alert color="red" mt="sm" p="xs">
                    {failed.map((a) => `${a.name}: ${a.error}`).join(' · ')}
                  </Alert>
                )}
                {!!lock.access?.length && (
                  <Group gap={6} mt="sm">
                    {lock.access.map((a) => (
                      <Badge key={a.memberId} variant="light" color={STATUS_COLOR[a.status]} style={{ textTransform: 'none' }}>
                        {a.name}
                      </Badge>
                    ))}
                  </Group>
                )}
              </Paper>
            )
          })}
        </Stack>
      )}
      {editing && (
        <LockForm
          lock={editing === 'new' ? null : editing}
          groups={groups}
          onClose={() => setEditing(null)}
          onSaved={(lock) => {
            report(lock)
            setEditing(null)
            qc.invalidateQueries({ queryKey: KEY })
          }}
        />
      )}
    </>
  )
}

function LockForm({
  lock,
  groups,
  onClose,
  onSaved,
}: {
  lock: SmartLock | null
  groups: { id: number; name: string }[]
  onClose: () => void
  onSaved: (lock: SmartLock) => void
}) {
  const { t } = useT()
  const { notify } = useToast()
  const qc = useQueryClient()
  const [form, setForm] = useState<LockInput>({
    name: lock?.name ?? '',
    smartlockId: lock?.smartlockId ?? 0,
    groupId: lock?.groupId ?? null,
    keypad: lock?.keypad ?? true,
    appOpen: lock?.appOpen ?? true,
  })
  const [busy, setBusy] = useState(false)
  const [asking, setAsking] = useState(false)
  const set = <K extends keyof LockInput>(k: K, v: LockInput[K]) => setForm((f) => ({ ...f, [k]: v }))

  const save = async () => {
    setBusy(true)
    try {
      onSaved(lock ? await updateLock(lock.id, form) : await createLock(form))
    } catch (err) {
      notify('error', err instanceof Error ? err.message : String(err))
    }
    setBusy(false)
  }
  const remove = async () => {
    if (!lock) return
    try {
      await deleteLock(lock.id)
      qc.invalidateQueries({ queryKey: KEY })
      onClose()
    } catch (err) {
      notify('error', err instanceof Error ? err.message : String(err))
    }
    setAsking(false)
  }

  return (
    <Modal opened onClose={onClose} title={lock ? t('locks.edit') : t('locks.add')}>
      <Stack gap="sm">
        <TextInput label={t('locks.name')} placeholder={t('locks.namePlaceholder')} value={form.name} maxLength={120} onChange={(e) => set('name', e.currentTarget.value)} required />
        <NumberInput
          label={t('locks.smartlockId')}
          description={t('locks.smartlockIdHint')}
          value={form.smartlockId || ''}
          onChange={(v) => set('smartlockId', typeof v === 'number' ? v : Number(v) || 0)}
          allowDecimal={false}
          allowNegative={false}
          hideControls
          required
        />
        <Select
          label={t('locks.group')}
          description={t('locks.groupHint')}
          data={[{ value: '', label: t('locks.everyone') }, ...groups.map((g) => ({ value: String(g.id), label: g.name }))]}
          value={form.groupId ? String(form.groupId) : ''}
          onChange={(v) => set('groupId', v ? Number(v) : null)}
          allowDeselect={false}
        />
        <Switch label={t('locks.keypadLabel')} description={t('locks.keypadHint')} checked={form.keypad} onChange={(e) => set('keypad', e.currentTarget.checked)} />
        <Switch label={t('locks.appOpenLabel')} description={t('locks.appOpenHint')} checked={form.appOpen} onChange={(e) => set('appOpen', e.currentTarget.checked)} />
        <Group justify="space-between" mt="sm">
          {lock ? (
            <Button variant="subtle" color="red" onClick={() => setAsking(true)}>
              {t('locks.delete')}
            </Button>
          ) : (
            <span />
          )}
          <Button onClick={save} loading={busy} disabled={!form.name.trim() || !form.smartlockId}>
            {t('locks.save')}
          </Button>
        </Group>
      </Stack>
      <ConfirmModal
        open={asking}
        onClose={() => setAsking(false)}
        onConfirm={remove}
        title={t('locks.delete')}
        body={t('locks.deleteConfirm', { name: lock?.name ?? '' })}
        confirmLabel={t('locks.delete')}
      />
    </Modal>
  )
}
