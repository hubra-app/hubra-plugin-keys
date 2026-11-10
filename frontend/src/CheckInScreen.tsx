import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ActionIcon, Alert, Avatar, Button, Group, Paper, Select, Stack, Text, TextInput } from '@mantine/core'
import { IconCamera, IconCameraOff, IconCheck, IconAlertTriangle, IconArrowBackUp, IconQrcode } from '@tabler/icons-react'
import { EmptyState, PageHead, formatDateTime, useT, useToast } from '@hubra/plugin-sdk'
import {
  cardToken,
  checkIn,
  listCheckins,
  listTodayEvents,
  lookupCard,
  undoCheckIn,
  type CardMember,
  type CheckIn,
} from './api'

type Result = { kind: 'ok' | 'again' | 'error'; member?: CardMember; text: string }

const NO_EVENT = 'none'

/** Scan member cards: at an event it marks them present, else it logs who came in. */
export function CheckInScreen() {
  const { t } = useT()
  const { notify } = useToast()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const events = useQuery({ queryKey: ['keys', 'checkin-events'], queryFn: listTodayEvents })
  const [where, setWhere] = useState<string | null>(null)
  const [place, setPlace] = useState('')
  const [code, setCode] = useState('')
  const [result, setResult] = useState<Result | null>(null)
  const [pending, setPending] = useState<{ card: string; member: CardMember } | null>(null)
  const [busy, setBusy] = useState(false)

  // The event running today is the default; with none, it is a plain check-in.
  useEffect(() => {
    if (where === null && events.data) setWhere(events.data.length === 1 ? String(events.data[0].id) : NO_EVENT)
  }, [events.data, where])
  const eventId = where && where !== NO_EVENT ? Number(where) : null
  const listKey = ['keys', 'checkins', eventId]
  const list = useQuery({ queryKey: listKey, queryFn: () => listCheckins(eventId) })

  const run = async (card: string) => {
    if (!card || busy) return
    setBusy(true)
    try {
      const res = await checkIn(card, eventId, eventId ? null : place.trim() || null)
      setResult({
        kind: res.checkIn.already ? 'again' : 'ok',
        member: res,
        text: res.checkIn.already
          ? t('checkin.again', { name: res.name, when: formatDateTime(res.checkIn.at) })
          : t('checkin.done', { name: res.name }),
      })
      qc.invalidateQueries({ queryKey: ['keys', 'checkins'] })
    } catch (err) {
      setResult({ kind: 'error', text: err instanceof Error ? err.message : String(err) })
    } finally {
      setBusy(false)
      setPending(null)
    }
  }

  // Opened from a card's QR code with the phone camera: show who it is first.
  const fromLink = params.get('card')
  useEffect(() => {
    if (!fromLink) return
    setParams({}, { replace: true })
    lookupCard(fromLink)
      .then((member) => setPending({ card: fromLink, member }))
      .catch((err) => setResult({ kind: 'error', text: err instanceof Error ? err.message : String(err) }))
  }, [fromLink, setParams])

  const submit = () => {
    const token = cardToken(code)
    setCode('')
    run(token)
  }

  const undo = async (c: CheckIn) => {
    try {
      await undoCheckIn(c.id)
      qc.invalidateQueries({ queryKey: ['keys', 'checkins'] })
    } catch (err) {
      notify('error', err instanceof Error ? err.message : String(err))
    }
  }

  const options = [
    { value: NO_EVENT, label: t('checkin.noEvent') },
    ...(events.data ?? []).map((e) => ({ value: String(e.id), label: e.time ? `${e.time} · ${e.title}` : e.title })),
  ]

  return (
    <>
      <PageHead title={t('checkin.title')} desc={t('checkin.desc')} />
      <Stack gap="md" maw={640}>
        {/* Who was just scanned comes first: on a phone the form fills the screen. */}
        {pending && (
          <Paper withBorder radius="md" p="md">
            <Group justify="space-between" wrap="nowrap">
              <Who member={pending.member} />
              <Button
                leftSection={<IconCheck size={16} />}
                loading={busy}
                disabled={!!pending.member.blocked}
                onClick={() => run(pending.card)}
              >
                {t('checkin.submit')}
              </Button>
            </Group>
          </Paper>
        )}

        {result && (
          <Alert
            color={result.kind === 'ok' ? 'green' : result.kind === 'again' ? 'yellow' : 'red'}
            icon={result.kind === 'error' ? <IconAlertTriangle size={18} /> : <IconCheck size={18} />}
            withCloseButton
            onClose={() => setResult(null)}
          >
            {result.member ? <Who member={result.member} line={result.text} /> : result.text}
          </Alert>
        )}

        <Paper withBorder radius="md" p="md">
          <Stack gap="sm">
            <Select label={t('checkin.where')} data={options} value={where} onChange={setWhere} allowDeselect={false} />
            {!eventId && (
              <TextInput
                label={t('checkin.place')}
                placeholder={t('checkin.placeHint')}
                value={place}
                maxLength={120}
                onChange={(e) => setPlace(e.currentTarget.value)}
              />
            )}
            <Group align="flex-end" wrap="nowrap">
              <TextInput
                style={{ flex: 1 }}
                label={t('checkin.code')}
                description={t('checkin.codeHint')}
                leftSection={<IconQrcode size={16} />}
                value={code}
                autoFocus
                onChange={(e) => setCode(e.currentTarget.value)}
                onKeyDown={(e) => e.key === 'Enter' && submit()}
              />
              <Button onClick={submit} loading={busy} disabled={!code.trim()}>
                {t('checkin.submit')}
              </Button>
            </Group>
            <Camera onCode={(text) => run(cardToken(text))} />
          </Stack>
        </Paper>

        <Text fw={700}>{t('checkin.today', { count: list.data?.length ?? 0 })}</Text>
        {!list.data?.length ? (
          <EmptyState icon={<IconQrcode size={28} />} title={t('checkin.none')} description={t('checkin.noneHint')} />
        ) : (
          <Stack gap={4}>
            {list.data.map((c) => (
              <Group key={c.id} justify="space-between" wrap="nowrap" px="sm" py={6} style={{ borderBottom: '1px solid var(--mantine-color-gray-2)' }}>
                <div style={{ minWidth: 0 }}>
                  <Text fw={600} fz="sm" truncate>
                    {c.name}
                  </Text>
                  <Text fz="xs" c="dimmed">
                    {formatDateTime(c.at)}
                    {c.place ? ` · ${c.place}` : ''}
                  </Text>
                </div>
                <ActionIcon variant="subtle" color="gray" aria-label={t('checkin.undo')} title={t('checkin.undo')} onClick={() => undo(c)}>
                  <IconArrowBackUp size={16} />
                </ActionIcon>
              </Group>
            ))}
          </Stack>
        )}
      </Stack>
    </>
  )
}

function Who({ member, line }: { member: CardMember; line?: string }) {
  const { t } = useT()
  return (
    <Group gap="sm" wrap="nowrap">
      <Avatar src={member.avatar} name={member.name} radius="xl" />
      <div>
        <Text fw={700}>{line ?? member.name}</Text>
        <Text fz="sm" c={member.blocked || member.expired ? 'red' : 'dimmed'}>
          {member.blocked ?? (member.expired ? t('checkin.expired') : t(`checkin.status.${member.status}`, member.status))}
        </Text>
      </div>
    </Group>
  )
}

type Detector = { detect: (src: HTMLVideoElement) => Promise<{ rawValue: string }[]> }

/** Scans with the device camera where the browser can read QR codes. */
function Camera({ onCode }: { onCode: (text: string) => void }) {
  const { t } = useT()
  const [on, setOn] = useState(false)
  const video = useRef<HTMLVideoElement>(null)
  // The latest handler, so a new render does not restart the camera.
  const handler = useRef(onCode)
  handler.current = onCode
  const supported = typeof window !== 'undefined' && 'BarcodeDetector' in window

  useEffect(() => {
    if (!on) return
    let stream: MediaStream | null = null
    let timer = 0
    let last = ''
    let lastAt = 0
    const Ctor = (window as unknown as { BarcodeDetector: new (o: object) => Detector }).BarcodeDetector
    const detector = new Ctor({ formats: ['qr_code'] })
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' } })
      .then((s) => {
        stream = s
        if (video.current) {
          video.current.srcObject = s
          void video.current.play()
        }
        timer = window.setInterval(async () => {
          if (!video.current || video.current.readyState < 2) return
          const [hit] = await detector.detect(video.current).catch(() => [])
          // The same card held in front of the camera counts once.
          if (hit && (hit.rawValue !== last || Date.now() - lastAt > 5000)) {
            last = hit.rawValue
            lastAt = Date.now()
            handler.current(hit.rawValue)
          }
        }, 400)
      })
      .catch(() => setOn(false))
    return () => {
      window.clearInterval(timer)
      stream?.getTracks().forEach((tr) => tr.stop())
    }
  }, [on])

  if (!supported) return null
  return (
    <Stack gap="xs">
      <Button
        variant="default"
        leftSection={on ? <IconCameraOff size={16} /> : <IconCamera size={16} />}
        onClick={() => setOn((v) => !v)}
      >
        {on ? t('checkin.cameraOff') : t('checkin.camera')}
      </Button>
      {on && <video ref={video} muted playsInline style={{ width: '100%', borderRadius: 8, background: '#000' }} />}
    </Stack>
  )
}
