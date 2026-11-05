import { useState } from 'react'
import { Badge, Button, Group, Image, Paper, Stack, Text } from '@mantine/core'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { IconId, IconRefresh } from '@tabler/icons-react'
import { ConfirmModal, formatDate, useT, useToast } from '@hubra/plugin-sdk'
import { getMyCard, renewMyCard } from './api'

/** The member's card on the account page: a QR code to be checked in with. */
export function MemberCardCard() {
  const { t } = useT()
  const { notify } = useToast()
  const qc = useQueryClient()
  const [asking, setAsking] = useState(false)
  const { data: card } = useQuery({ queryKey: ['keys', 'card'], queryFn: getMyCard })
  if (!card) return null

  const renew = async () => {
    try {
      qc.setQueryData(['keys', 'card'], await renewMyCard())
      notify('success', t('card.renewed'))
    } catch (err) {
      notify('error', err instanceof Error ? err.message : String(err))
    }
    setAsking(false)
  }

  return (
    <Paper withBorder shadow="sm" radius="lg">
      <Group p="md" gap="sm" style={{ borderBottom: '1px solid var(--mantine-color-gray-3)' }}>
        <IconId size={16} style={{ color: '#6b7480' }} />
        <Text fw={700} fz="md">
          {t('card.title')}
        </Text>
      </Group>
      <Stack p="md" gap="sm" align="center">
        <Image src={card.qr} alt={t('card.qrAlt')} w={220} h={220} fit="contain" style={{ background: '#fff', borderRadius: 8 }} />
        <Text fw={700} fz="lg">
          {card.name}
        </Text>
        <Group gap="xs">
          <Badge variant="light" style={{ textTransform: 'none' }}>
            {t(`card.status.${card.status}`, card.status)}
          </Badge>
          {card.until && (
            <Text fz="sm" c="dimmed">
              {t('card.until', { date: formatDate(card.until) })}
            </Text>
          )}
        </Group>
        <Text fz="xs" c="dimmed" ta="center">
          {t('card.hint')}
        </Text>
        <Button variant="subtle" size="xs" leftSection={<IconRefresh size={14} />} onClick={() => setAsking(true)}>
          {t('card.renew')}
        </Button>
      </Stack>
      <ConfirmModal
        open={asking}
        onClose={() => setAsking(false)}
        onConfirm={renew}
        title={t('card.renew')}
        body={t('card.renewConfirm')}
        confirmLabel={t('card.renew')}
      />
    </Paper>
  )
}
