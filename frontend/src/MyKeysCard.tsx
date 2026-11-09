import { useState } from 'react'
import { Button, Group, Paper, Text } from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { IconKey } from '@tabler/icons-react'
import { useT } from '@hubra/plugin-sdk'
import { listMyKeys } from './api'

/** Keys and codes the member holds, is assigned to (directly or through a
 * group) or every member may use (inventory.keys module). A code is hidden
 * until tapped. */
export function MyKeysCard() {
  const { t } = useT()
  const { data: keys = [] } = useQuery({
    queryKey: ['keys', 'mine'],
    queryFn: listMyKeys,
  })
  if (keys.length === 0) return null
  return (
    <Paper withBorder shadow="sm" radius="lg">
      <Group p="md" gap="sm" style={{ borderBottom: '1px solid var(--mantine-color-gray-3)' }}>
        <IconKey size={16} style={{ color: '#6b7480' }} />
        <Text fw={700} fz="md">
          {t('account.myKeysCodes', 'My keys and codes')}
        </Text>
      </Group>
      {keys.map((k) => (
        <Group
          key={k.id}
          justify="space-between"
          px="md"
          py="sm"
          style={{ borderBottom: '1px solid var(--mantine-color-gray-2)' }}
        >
          <div>
            <Text fw={600} fz="sm">
              {k.label}
              {k.number && (
                <Text span c="dimmed" fz="xs" ml={8}>
                  {k.number}
                </Text>
              )}
            </Text>
            {k.opens && (
              <Text fz="xs" c="dimmed">
                {k.opens}
              </Text>
            )}
          </div>
          {k.kind === 'code' && k.code ? (
            <CodeValue code={k.code} />
          ) : k.depositChf && k.mine ? (
            <Text fz="xs" c="dimmed" className="num">
              {t('account.keyDeposit', 'Deposit CHF {{amount}}', {
                amount: k.depositChf,
              })}
            </Text>
          ) : null}
        </Group>
      ))}
    </Paper>
  )
}

function CodeValue({ code }: { code: string }) {
  const { t } = useT()
  const [open, setOpen] = useState(false)
  return open ? (
    <Text fw={700} className="num" onClick={() => setOpen(false)} style={{ cursor: 'pointer' }}>
      {code}
    </Text>
  ) : (
    <Button size="compact-xs" variant="default" onClick={() => setOpen(true)}>
      {t('account.showCode', 'Show code')}
    </Button>
  )
}
