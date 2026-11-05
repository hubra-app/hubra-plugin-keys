import { useState } from 'react'
import { Button, Group, Paper, Text } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { IconDoor, IconLockOpen } from '@tabler/icons-react'
import { useT, useToast } from '@hubra/plugin-sdk'
import { listMyLocks, openLock, type MyLock } from './api'

/** Doors the member may open: their keypad code and an Open button. */
export function MyDoorsCard() {
  const { t } = useT()
  const { data: locks = [] } = useQuery({ queryKey: ['keys', 'locks', 'mine'], queryFn: listMyLocks })
  if (locks.length === 0) return null
  return (
    <Paper withBorder shadow="sm" radius="lg">
      <Group p="md" gap="sm" style={{ borderBottom: '1px solid var(--mantine-color-gray-3)' }}>
        <IconDoor size={16} style={{ color: '#6b7480' }} />
        <Text fw={700} fz="md">
          {t('locks.mine')}
        </Text>
      </Group>
      {locks.map((lock) => (
        <Door key={lock.id} lock={lock} />
      ))}
    </Paper>
  )
}

function Door({ lock }: { lock: MyLock }) {
  const { t } = useT()
  const { notify } = useToast()
  const [busy, setBusy] = useState(false)
  const open = async () => {
    setBusy(true)
    try {
      await openLock(lock.id)
      notify('success', t('locks.opened', { name: lock.name }))
    } catch (err) {
      notify('error', err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }
  return (
    <Group justify="space-between" px="md" py="sm" wrap="nowrap" style={{ borderBottom: '1px solid var(--mantine-color-gray-2)' }}>
      <div>
        <Text fw={600} fz="sm">
          {lock.name}
        </Text>
        {lock.code && (
          <Text fz="sm" c="dimmed">
            {t('locks.yourCode')}{' '}
            <Text span ff="monospace" fw={700} c="var(--mantine-color-text)" style={{ letterSpacing: 2 }}>
              {lock.code}
            </Text>
          </Text>
        )}
      </div>
      {lock.appOpen && (
        <Button size="xs" variant="light" leftSection={<IconLockOpen size={14} />} loading={busy} onClick={open}>
          {t('locks.open')}
        </Button>
      )}
    </Group>
  )
}
