# Changelog

## Unreleased

- Security: only key managers (`keys.keys.manage`) can reveal a key's code. Who may only view keys sees that a key has a code, not the code.
- Security: the old club member cards no longer check anyone in, and their table `member_cards` is dropped (migration `f4a9c2e7b1d3`). Their codes could no longer be renewed or revoked. Check-in scans the member badge.
- Check-in on a Hubra without `members.badge.lookup` answers "update Hubra" (`BADGE_LOOKUP_MISSING`, 503) instead of calling every badge unknown. **At release: set `hubra:` in plugin.yaml to the first Hubra release after 0.2.5** (it has the lookup).
- Security: codes under Meine Schlüssel follow membership like the door codes. A member who is suspended, inactive or whose membership has ended still sees the key, but not its code.
- Security: undoing a check-in is written to the audit log, since check-ins are also the log of doors opened from the app.
- Security: key fields are checked for length (label 120, number 100, opens 255, notes 10,000, code 200) and the deposit for range, instead of failing with a server error. `opens` must be text.
- A keypad code that can no longer be decrypted no longer stops the lock sync or the member's door page; while not active on the lock it is replaced by a new one.
- Key, hand-out and lock dialogs use the shared footer (Abbrechen, main action, delete at the left) and save on Enter; the deposit has no arrows.
- **A key can carry a code**: any key, card or fob can have a code next to it (a key safe, the lock's combination), stored encrypted like a code key. Managers see it with "Anzeigen" (audited), the holder and the members it is assigned to see it under Meine Schlüssel. "Code entfernen" removes it.
- German texts are in Standard German now; they were still in Swiss German dialect. The Nuki hint points at Einstellungen › Module › Schlüssel (there is no "Verwalten" page).
- **Check-in scans the member badge**: the one badge per person from My Account and Google Wallet (`HB-XXXX-XXXX`), through Hubra's `members.badge.lookup` contract; the number can also be typed. The club's own member card is gone from the account page (and `GET /keys/card`, `POST /keys/card/renew` with it), so members have one QR code instead of two. Cards members already have (printed, screenshots) still check in; a later release drops `member_cards`. Needs Hubra with `members.badge.lookup` (the release after 0.2.5).
- Dashboard widgets: **Meine Schlüssel** (keys and codes the member holds or may use, without the code itself) and **Ausgegebene Schlüssel** (how many are handed out and how many are lost; needs `keys.keys.read`).

## 1.5.0

- Gives the standard roles access when a club first switches it on (`role_defaults`, docs/roles.md in hubra-app/hubra): Vorstand Ansehen. Roles without access don't see it; their own data from it stays on their profile. Needs Hubra 0.2.5 or later.
- Dashboard widgets: **Meine Schlüssel** (keys and codes the member holds or may use, without the code itself) and **Ausgegebene Schlüssel** (how many are handed out and how many are lost; needs `keys.keys.read`).

## 1.4.2

1.4.1 was tagged but couldn't be signed, so it was never released. 1.4.2 is the same plugin, signed. What it brings:

- Keys live in Inventory: each key is an item of the type "Key", shown in
  the inventory list, its filters, the "By type" view and search with the
  club's other items. The Keys page is gone; its menu entry too, and
  `/app/inventory/keys` opens the inventory on keys (`?type=Key`), whose
  table shows number, status and who holds each key.
- A key's inventory page has a key panel: status, holder, kind, what it
  opens, deposit, and the buttons to hand it out, take it back, mark it lost
  or found and retire it. Who holds it is the item's "Held by".
- The handover log moved into the item's history in Inventory. Handovers
  from before are moved there (with their dates) by the job
  `keys-link-items` (every 5 minutes) after the upgrade, which also gives
  every existing key its inventory item. Nothing is lost; `key_handovers` is
  only used while a key has no item yet. New column `keys.item_id`.
- Both ways: a key added, renamed or deleted here changes its item, and an
  item of the type "Key" added (Inventory → New item → Key), renamed or
  deleted in Inventory changes the key. Keys owns the status and holder
  (handed out = "in use"); one set by hand in Inventory is put back. An item
  that stops being a key deletes the key, unless somebody holds it.
- **Codes are keys too**: a key of the new kind "code" keeps a door code,
  lock combination or passcode, encrypted (`keys.secret`, re-encrypted on
  key rotation). Managers see it with "Show" (each look is in the audit
  log); a code isn't handed out. The Codes plugin's codes come in as code
  keys through its query `codes.codes.export` (Codes 2.1) in the same job,
  each once; after that Codes can be switched off and uninstalled.
- **Who may use a key**: every member (public), or several members and
  groups at once (new table `key_assignments`). "My keys and codes" on the
  account page lists what a member holds, is assigned to (directly or
  through a group) or every member may use, with the code behind a "Show"
  button. Setting a Codes code on a key (`code_id`) is gone.
- Goes through Inventory's contracts only (`inventory.items.save`,
  `.delete`, `.history.add`, `.get`, events `inventory.item.saved` and
  `.deleted`): needs Inventory 2.2 or newer.

## 1.4.1

1.4.0 was tagged but couldn't be signed, so it was never released. 1.4.1 is the same plugin, signed. What 1.4.0 brings:

- Keys live in Inventory: each key is an item of the type "Key", shown in
  the inventory list, its filters, the "By type" view and search with the
  club's other items. The Keys page is gone; its menu entry too, and
  `/app/inventory/keys` opens the inventory on keys (`?type=Key`), whose
  table shows number, status and who holds each key.
- A key's inventory page has a key panel: status, holder, kind, what it
  opens, deposit, and the buttons to hand it out, take it back, mark it lost
  or found and retire it. Who holds it is the item's "Held by".
- The handover log moved into the item's history in Inventory. Handovers
  from before are moved there (with their dates) by the job
  `keys-link-items` (every 5 minutes) after the upgrade, which also gives
  every existing key its inventory item. Nothing is lost; `key_handovers` is
  only used while a key has no item yet. New column `keys.item_id`.
- Both ways: a key added, renamed or deleted here changes its item, and an
  item of the type "Key" added (Inventory → New item → Key), renamed or
  deleted in Inventory changes the key. Keys owns the status and holder
  (handed out = "in use"); one set by hand in Inventory is put back. An item
  that stops being a key deletes the key, unless somebody holds it.
- **Codes are keys too**: a key of the new kind "code" keeps a door code,
  lock combination or passcode, encrypted (`keys.secret`, re-encrypted on
  key rotation). Managers see it with "Show" (each look is in the audit
  log); a code isn't handed out. The Codes plugin's codes come in as code
  keys through its query `codes.codes.export` (Codes 2.1) in the same job,
  each once; after that Codes can be switched off and uninstalled.
- **Who may use a key**: every member (public), or several members and
  groups at once (new table `key_assignments`). "My keys and codes" on the
  account page lists what a member holds, is assigned to (directly or
  through a group) or every member may use, with the code behind a "Show"
  button. Setting a Codes code on a key (`code_id`) is gone.
- Goes through Inventory's contracts only (`inventory.items.save`,
  `.delete`, `.history.add`, `.get`, events `inventory.item.saved` and
  `.deleted`): needs Inventory 2.2 or newer.

## 1.4.0

- Keys live in Inventory: each key is an item of the type "Key", shown in
  the inventory list, its filters, the "By type" view and search with the
  club's other items. The Keys page is gone; its menu entry too, and
  `/app/inventory/keys` opens the inventory on keys (`?type=Key`), whose
  table shows number, status and who holds each key.
- A key's inventory page has a key panel: status, holder, kind, what it
  opens, deposit, and the buttons to hand it out, take it back, mark it lost
  or found and retire it. Who holds it is the item's "Held by".
- The handover log moved into the item's history in Inventory. Handovers
  from before are moved there (with their dates) by the job
  `keys-link-items` (every 5 minutes) after the upgrade, which also gives
  every existing key its inventory item. Nothing is lost; `key_handovers` is
  only used while a key has no item yet. New column `keys.item_id`.
- Both ways: a key added, renamed or deleted here changes its item, and an
  item of the type "Key" added (Inventory → New item → Key), renamed or
  deleted in Inventory changes the key. Keys owns the status and holder
  (handed out = "in use"); one set by hand in Inventory is put back. An item
  that stops being a key deletes the key, unless somebody holds it.
- **Codes are keys too**: a key of the new kind "code" keeps a door code,
  lock combination or passcode, encrypted (`keys.secret`, re-encrypted on
  key rotation). Managers see it with "Show" (each look is in the audit
  log); a code isn't handed out. The Codes plugin's codes come in as code
  keys through its query `codes.codes.export` (Codes 2.1) in the same job,
  each once; after that Codes can be switched off and uninstalled.
- **Who may use a key**: every member (public), or several members and
  groups at once (new table `key_assignments`). "My keys and codes" on the
  account page lists what a member holds, is assigned to (directly or
  through a group) or every member may use, with the code behind a "Show"
  button. Setting a Codes code on a key (`code_id`) is gone.
- Goes through Inventory's contracts only (`inventory.items.save`,
  `.delete`, `.history.add`, `.get`, events `inventory.item.saved` and
  `.deleted`): needs Inventory 2.2 or newer.

## 1.3.0

- Member cards: every member has a QR code on their account page. A new code
  ends the old one.
- Check-in screen: scan member cards with the phone camera, a QR scanner or
  the camera in the screen. At an event of the day the member is marked
  present on its attendance list; without one it logs who came in and where.
  New permission `keys.checkins.create`. New tables `member_cards`, `checkins`.
- Smart locks (Nuki): each member who may open a door (all members or one
  group) gets their own keypad code, removed again when the membership ends,
  the member is suspended or leaves the group. Optional Open button in the app,
  logged as a check-in. Synced every 15 minutes. New setting `nuki_token`,
  permission `keys.locks.manage`, tables `smart_locks`, `lock_access`.

## 1.2.1

- Release on a pushed v* tag (works with immutable releases) (#8)

## 1.2.0

- Works without the Codes plugin. Codes is no longer built into Hubra; a
  key's door code is checked against the Codes plugin only when that is
  installed. The database link from keys to codes is removed, so either
  plugin can be installed or removed on its own.

## 1.1.0

Built for Hubra 0.2 (Mantine 9, plugin host API 2). Needs Hubra 0.2 or newer.

## 1.0.1

- "My keys" no longer shows the managers' notes on a key, and no longer
  lists retired keys.
- A label, number or note that isn't text, or a deposit of "NaN", is refused
  with a message instead of a server error.

## 1.0.0

First release as a plugin. Before, Keys was built into Hubra.
