import { registerPlugin } from '@hubra/plugin-sdk'
import { IconQrcode } from '@tabler/icons-react'
import { CheckInScreen } from './CheckInScreen'
import { KeysScreen } from './KeysScreen'
import { LocksScreen } from './LocksScreen'
import { MemberCardCard } from './MemberCardCard'
import { MyDoorsCard } from './MyDoorsCard'
import { MyKeysCard } from './MyKeysCard'
import translations from './translations.json'

registerPlugin({
  id: 'keys',
  routes: [
    {
      path: 'inventory/keys',
      module: 'inventory.keys',
      perm: 'keys.keys.read',
      component: KeysScreen,
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
    { slot: 'account.cards', module: 'inventory.keys', component: MemberCardCard },
    { slot: 'account.cards', module: 'inventory.keys', component: MyDoorsCard },
    { slot: 'account.cards', module: 'inventory.keys', component: MyKeysCard },
  ],
  // The check-in nav entry in hubra_keys/__init__.py names this icon.
  icons: { qrcode: IconQrcode },
  translations,
})
