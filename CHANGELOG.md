# Changelog

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
