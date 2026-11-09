import { registerPlugin } from '@hubra/plugin-sdk'
import { Navigate } from 'react-router-dom'
import { IconQrcode } from '@tabler/icons-react'
import { CheckInScreen } from './CheckInScreen'
import { KeyItemPanel } from './KeyItemPanel'
import { LocksScreen } from './LocksScreen'
import { MemberCardCard } from './MemberCardCard'
import { MyDoorsCard } from './MyDoorsCard'
import { MyKeysCard } from './MyKeysCard'
import translations from './translations.json'

function KeysMoved() {
  return <Navigate to="/app/inventory?type=Key" replace />
}

registerPlugin({
  id: 'keys',
  routes: [
    // Keys have no page of their own any more: they are inventory items of
    // the type "Key". Old links land on the inventory's key view.
    {
      path: 'inventory/keys',
      module: 'inventory.keys',
      component: KeysMoved,
    },
    {
      path: 'inventory/checkin',
      module: 'inventory.keys',
      perm: 'keys.checkins.create',
      component: CheckInScreen,
    },
    {
      path: 'inventory/locks',
      module: 'inventory.keys',
      perm: 'keys.locks.manage',
      component: LocksScreen,
    },
  ],
  slots: [
    // A key is an inventory item of the type "Key": its page there shows the
    // key's details, handovers and history.
    {
      slot: 'inventory.item',
      module: 'inventory.keys',
      perm: 'keys.keys.read',
      component: KeyItemPanel,
    },
    { slot: 'account.cards', module: 'inventory.keys', component: MemberCardCard },
    { slot: 'account.cards', module: 'inventory.keys', component: MyDoorsCard },
    { slot: 'account.cards', module: 'inventory.keys', component: MyKeysCard },
  ],
  // The check-in nav entry in hubra_keys/__init__.py names this icon.
  icons: { qrcode: IconQrcode },
  translations,
})
