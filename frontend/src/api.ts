import { apiFetch } from '@hubra/plugin-sdk'

export type KeyKind = 'key' | 'card' | 'fob'
export type KeyStatus = 'available' | 'issued' | 'lost' | 'retired'

export interface KeyHandover {
  id: number
  action: 'issue' | 'return' | 'lost' | 'found' | 'retire'
  memberId: number | null
  memberName: string | null
  byName: string | null
  note: string | null
  at: string
}

export interface ClubKey {
  id: number
  label: string
  number: string | null
  kind: KeyKind
  opens: string | null
  status: KeyStatus
  holderId: number | null
  holderName: string | null
  depositChf: string | null
  codeId: number | null
  notes: string | null
  updatedAt: string | null
  history?: KeyHandover[]
}

export interface KeyInput {
  label?: string
  number?: string | null
  kind?: KeyKind
  opens?: string | null
  deposit_chf?: number | null
  notes?: string | null
}

export const listKeys = () => apiFetch<ClubKey[]>('/keys/')
export const listMyKeys = () => apiFetch<ClubKey[]>('/keys/mine')
export const getKey = (id: number) => apiFetch<ClubKey>(`/keys/${id}`)

export const createKey = (input: KeyInput) =>
  apiFetch<ClubKey>('/keys/', { method: 'POST', body: JSON.stringify(input) })

export const updateKey = (id: number, input: KeyInput) =>
  apiFetch<ClubKey>(`/keys/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })

export const deleteKey = (id: number) => apiFetch<void>(`/keys/${id}`, { method: 'DELETE' })

export const issueKey = (id: number, memberId: number, note?: string) =>
  apiFetch<ClubKey>(`/keys/${id}/issue`, {
    method: 'POST',
    body: JSON.stringify({ member_id: memberId, note }),
  })

export type KeyAction = 'return' | 'lost' | 'found' | 'retire'

export const keyAction = (id: number, action: KeyAction, note?: string) =>
  apiFetch<ClubKey>(`/keys/${id}/${action}`, {
    method: 'POST',
    body: JSON.stringify({ note }),
  })

// ── Member card and check-in ────────────────────────────────────────────────

export interface MemberCard {
  name: string
  memberId: number
  status: string
  since: string | null
  until: string | null
  token: string
  qr: string
  renewedAt: string | null
}

export interface CardMember {
  memberId: number
  name: string
  status: string
  avatar: string | null
  until: string | null
  expired: boolean
  blocked: string | null
}

export interface CheckIn {
  id: number
  memberId: number
  name: string | null
  eventId: number | null
  place: string | null
  at: string
  already: boolean
}

export interface TodayEvent {
  id: number
  title: string
  time: string | null
  location: string | null
}

/** The app's check-in screen; the card's QR code points here. */
export function checkinLink() {
  const appRoot = window.location.origin + window.location.pathname.split('/app/')[0]
  return `${appRoot}/app/inventory/checkin?card=`
}

/** The token from a scanned code: a whole link or just the token. */
export function cardToken(scanned: string) {
  const text = scanned.trim()
  const m = text.match(/[?&]card=([^&#\s]+)/)
  return m ? decodeURIComponent(m[1]) : text
}

const link = () => encodeURIComponent(checkinLink())
export const getMyCard = () => apiFetch<MemberCard>(`/keys/card?link=${link()}`)
export const renewMyCard = () => apiFetch<MemberCard>(`/keys/card/renew?link=${link()}`, { method: 'POST' })

export const lookupCard = (card: string) =>
  apiFetch<CardMember>(`/keys/checkins/lookup?card=${encodeURIComponent(card)}`)
export const listTodayEvents = () => apiFetch<TodayEvent[]>('/keys/checkins/events')
export const listCheckins = (eventId: number | null) =>
  apiFetch<CheckIn[]>(`/keys/checkins${eventId ? `?eventId=${eventId}` : ''}`)
export const checkIn = (card: string, eventId: number | null, place: string | null) =>
  apiFetch<CardMember & { checkIn: CheckIn }>('/keys/checkins', {
    method: 'POST',
    body: JSON.stringify({ card, eventId, place }),
  })
export const undoCheckIn = (id: number) => apiFetch<void>(`/keys/checkins/${id}`, { method: 'DELETE' })

// ── Smart locks ─────────────────────────────────────────────────────────────

export interface LockAccess {
  memberId: number
  name: string | null
  status: 'pending' | 'active' | 'failed'
  error: string | null
}

export interface SmartLock {
  id: number
  name: string
  smartlockId: number
  groupId: number | null
  keypad: boolean
  appOpen: boolean
  syncedAt: string | null
  access?: LockAccess[]
  sync?: { added: number; removed: number; failed: number }
}

export interface LockInput {
  name: string
  smartlockId: number
  groupId: number | null
  keypad: boolean
  appOpen: boolean
}

export interface MyLock {
  id: number
  name: string
  code: string | null
  appOpen: boolean
}

export const listLocks = () =>
  apiFetch<{ configured: boolean; locks: SmartLock[]; groups: { id: number; name: string }[] }>('/keys/locks')
export const createLock = (input: LockInput) =>
  apiFetch<SmartLock>('/keys/locks', { method: 'POST', body: JSON.stringify(input) })
export const updateLock = (id: number, input: Partial<LockInput>) =>
  apiFetch<SmartLock>(`/keys/locks/${id}`, { method: 'PATCH', body: JSON.stringify(input) })
export const deleteLock = (id: number) => apiFetch<void>(`/keys/locks/${id}`, { method: 'DELETE' })
export const syncLock = (id: number) => apiFetch<SmartLock>(`/keys/locks/${id}/sync`, { method: 'POST' })
export const listMyLocks = () => apiFetch<MyLock[]>('/keys/locks/mine')
export const openLock = (id: number) => apiFetch<{ opened: boolean }>(`/keys/locks/${id}/open`, { method: 'POST' })
