# Changelog

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
