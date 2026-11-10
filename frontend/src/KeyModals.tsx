import { useMemo, useState } from 'react'
import {
  Button,
  Checkbox,
  MultiSelect,
  NumberInput,
  PasswordInput,
  Select,
  Textarea,
  TextInput,
} from '@mantine/core'
import { useQuery } from '@tanstack/react-query'
import { Field, Modal, listMembers, useT } from '@hubra/plugin-sdk'
import {
  createKey,
  issueKey,
  keyOptions,
  updateKey,
  type ClubKey,
  type KeyInput,
  type KeyKind,
  type KeyStatus,
} from './api'

/** Shared by the Keys page and the key panel on a key's inventory page. */

export const STATUS_COLORS: Record<KeyStatus, string> = {
  available: '#1f9d57',
  issued: '#2f6fd6',
  lost: '#d64545',
  retired: '#99a2ac',
}

const EMPTY: KeyInput = {
  label: '',
  number: '',
  kind: 'key',
  opens: '',
  deposit_chf: null,
  notes: '',
}

/** Adds a key (`'new'`) or edits one. A new key is a new inventory item too. */
export function KeyFormModal({
  clubKey,
  onClose,
  onSaved,
  onError,
}: {
  clubKey: ClubKey | 'new'
  onClose: () => void
  onSaved: (key: ClubKey) => void
  onError: (err: unknown) => void
}) {
  const { t } = useT()
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState<KeyInput>(
    clubKey === 'new'
      ? EMPTY
      : {
          label: clubKey.label,
          number: clubKey.number ?? '',
          kind: clubKey.kind,
          opens: clubKey.opens ?? '',
          deposit_chf: clubKey.depositChf ? Number(clubKey.depositChf) : null,
          notes: clubKey.notes ?? '',
          public: !!clubKey.public,
          member_ids: (clubKey.members ?? []).map((m) => m.id),
          group_ids: (clubKey.groups ?? []).map((g) => g.id),
        },
  )
  // A new code is typed in; an existing one is kept unless replaced.
  const [code, setCode] = useState('')
  const [clearCode, setClearCode] = useState(false)
  const { data: members } = useQuery({
    queryKey: ['members'],
    queryFn: () => listMembers({ pageSize: 500 }),
  })
  const { data: options } = useQuery({ queryKey: ['keys', 'options'], queryFn: keyOptions })

  const save = async () => {
    const body: KeyInput = {
      ...form,
      number: form.number || null,
      opens: form.opens || null,
      notes: form.notes || null,
      ...(code ? { code } : clearCode ? { code: '' } : {}),
    }
    setBusy(true)
    try {
      onSaved(clubKey === 'new' ? await createKey(body) : await updateKey(clubKey.id, body))
    } catch (err) {
      onError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={clubKey === 'new' ? t('keys.add', 'Add key') : t('keys.edit', 'Edit key')}
      footer={
        <>
          <Button variant="subtle" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button variant="default" onClick={save} loading={busy} disabled={!form.label?.trim()}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label={t('keys.label', 'Label')}>
          <TextInput
            value={form.label ?? ''}
            onChange={(e) => setForm({ ...form, label: e.currentTarget.value })}
            placeholder={t('keys.labelPlaceholder', 'Front door')}
          />
        </Field>
        <Field label={t('keys.number', 'Number')}>
          <TextInput
            value={form.number ?? ''}
            onChange={(e) => setForm({ ...form, number: e.currentTarget.value })}
            placeholder="A-12"
          />
        </Field>
        <Field label={t('keys.kind', 'Type')}>
          <Select
            value={form.kind}
            onChange={(v) => setForm({ ...form, kind: (v as KeyKind) ?? 'key' })}
            data={(['key', 'card', 'fob', 'code'] as const).map((k) => ({
              value: k,
              label: t(`keys.kinds.${k}`, k),
            }))}
            allowDeselect={false}
          />
        </Field>
        {/* A code key is its code; any other key may carry one too (a key
            safe, the lock's combination). Stored encrypted. */}
        <Field
          label={form.kind === 'code' ? t('keys.code', 'Code') : t('keys.codeOptional', 'Code (optional)')}
          hint={form.kind === 'code' ? undefined : t('keys.codeHint', 'For example the key safe or the combination of the lock')}
        >
          <PasswordInput
            value={code}
            onChange={(e) => {
              setCode(e.currentTarget.value)
              setClearCode(false)
            }}
            placeholder={
              clubKey !== 'new' && clubKey.hasCode
                ? clearCode
                  ? t('keys.codeRemoved', 'The code is removed when you save')
                  : t('keys.codeKeep', 'Leave empty to keep the code')
                : '1234'
            }
            autoComplete="off"
          />
          {clubKey !== 'new' && clubKey.hasCode && !code && !clearCode && form.kind !== 'code' && (
            <Button size="compact-xs" variant="subtle" color="red" mt={4} onClick={() => setClearCode(true)}>
              {t('keys.codeRemove', 'Remove code')}
            </Button>
          )}
        </Field>
        <Field label={t('keys.access', 'Who may use it')}>
          <Checkbox
            checked={!!form.public}
            onChange={(e) => setForm({ ...form, public: e.currentTarget.checked })}
            label={t('keys.public', 'Every member (public)')}
            mb={8}
          />
          {!form.public && (
            <>
              <MultiSelect
                searchable
                mb={8}
                placeholder={t('keys.assignMembers', 'Members …')}
                data={(members?.members ?? []).map((m) => ({ value: String(m.id), label: m.name }))}
                value={(form.member_ids ?? []).map(String)}
                onChange={(v) => setForm({ ...form, member_ids: v.map(Number) })}
              />
              <MultiSelect
                searchable
                placeholder={t('keys.assignGroups', 'Groups …')}
                data={(options?.groups ?? []).map((g) => ({ value: String(g.id), label: g.name }))}
                value={(form.group_ids ?? []).map(String)}
                onChange={(v) => setForm({ ...form, group_ids: v.map(Number) })}
              />
            </>
          )}
        </Field>
        <Field label={t('keys.opens', 'Opens')}>
          <TextInput
            value={form.opens ?? ''}
            onChange={(e) => setForm({ ...form, opens: e.currentTarget.value })}
            placeholder={t('keys.opensPlaceholder', 'Main entrance, workshop')}
          />
        </Field>
        <Field label={t('keys.deposit', 'Deposit')}>
          <NumberInput
            value={form.deposit_chf ?? ''}
            onChange={(v) => setForm({ ...form, deposit_chf: v === '' ? null : Number(v) })}
            min={0}
            decimalScale={2}
            prefix="CHF "
          />
        </Field>
        <Field label={t('keys.notes', 'Notes')}>
          <Textarea
            value={form.notes ?? ''}
            onChange={(e) => setForm({ ...form, notes: e.currentTarget.value })}
            rows={3}
          />
        </Field>
      </div>
    </Modal>
  )
}

/** Hands a key out to a member. */
export function IssueModal({
  clubKey,
  onClose,
  onDone,
  onError,
}: {
  clubKey: ClubKey
  onClose: () => void
  onDone: () => void
  onError: (err: unknown) => void
}) {
  const { t } = useT()
  const [memberId, setMemberId] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const { data } = useQuery({
    queryKey: ['members'],
    queryFn: () => listMembers({ pageSize: 500 }),
  })
  const options = useMemo(
    () => (data?.members ?? []).map((m) => ({ value: m.id, label: m.name })),
    [data],
  )

  const submit = async () => {
    if (!memberId) return
    setBusy(true)
    try {
      await issueKey(clubKey.id, Number(memberId), note || undefined)
      onDone()
    } catch (err) {
      onError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t('keys.issueTitle', 'Hand out {{name}}', { name: clubKey.label })}
      footer={
        <>
          <Button variant="subtle" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button variant="default" onClick={submit} loading={busy} disabled={!memberId}>
            {t('keys.issue', 'Hand out')}
          </Button>
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label={t('keys.member', 'Member')}>
          <Select
            searchable
            data={options}
            value={memberId}
            onChange={setMemberId}
            placeholder={t('keys.pickMember', 'Search member…')}
          />
        </Field>
        <Field label={t('keys.note', 'Note')}>
          <TextInput value={note} onChange={(e) => setNote(e.currentTarget.value)} />
        </Field>
      </div>
    </Modal>
  )
}

