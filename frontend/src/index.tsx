import { registerPlugin } from '@hubra/plugin-sdk'
import { IconQrcode } from '@tabler/icons-react'
import { CheckInScreen } from './CheckInScreen'
import { KeysScreen } from './KeysScreen'
import { MemberCardCard } from './MemberCardCard'
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
  ],
  slots: [
    { slot: 'account.cards', module: 'inventory.keys', component: MemberCardCard },
    { slot: 'account.cards', module: 'inventory.keys', component: MyKeysCard },
  ],
  // The check-in nav entry in hubra_keys/__init__.py names this icon.
  icons: { qrcode: IconQrcode },
  translations,
})
