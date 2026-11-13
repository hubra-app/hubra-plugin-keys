# Keys

[![Test and release](https://github.com/hubra-app/hubra-plugin-keys/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/hubra-app/hubra-plugin-keys/actions/workflows/release.yml?query=branch%3Amain) [![License: all rights reserved](https://img.shields.io/badge/license-all%20rights%20reserved-lightgrey)](LICENSE) [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-bitsandbricks-ffdd00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/bitsandbricks)

A plugin for [Hubra](https://hubra.club). Physical keys, cards and fobs: who holds which, with a handover log. Members see their keys on their account page.

**Version** 1.6.0 · **Works with** Hubra >=0.2.6,<1 · **Plugin id** `keys`

## Keys in the inventory

Keys have no page of their own: each key, card or fob is an inventory item of
the type **Key**. Add one in Inventory with the type Key; filter the list by
Key (the table then shows number, status and who holds each key) or use the
"By type" view. The key's inventory page has the key panel (kind, what it
opens, deposit, hand out, take back, lost, found, retire); the handovers are
in the item's history there. Keys talks to Inventory through its contracts
only, never its code or tables.

A key of the kind **code** is a door code or passcode, stored encrypted. A
key or code is for every member (public) or assigned to several members and
groups; members find theirs under *My keys and codes* on their account page.
Codes from the Codes plugin move in by themselves (Codes 2.1 or newer); then
Codes can be uninstalled.

## Check-in with the member badge

Every member has one member badge in Hubra: under *My Account* and, where the
platform offers it, in Google Wallet. Its QR code holds the badge number (such
as `HB-7K3M-Q9TX`), the same in every club. Whoever has the right **Check
members in with their member badge** (`keys.checkins.create`) opens
*Check-in* and scans:

- with a USB or Bluetooth QR scanner, which types the number into the field;
- in Chrome on Android, with the camera button on the screen itself;
- or types the badge number by hand (case, dashes and the `HB` don't matter).

At an event of the day, a check-in marks the member present on the event's
attendance list (an "excused" becomes "present"). Without an event it logs who
came in and where (door, open workshop). The same badge twice counts once.
Suspended members and members who left are refused; an ended membership is
shown in red. Someone with a badge who isn't a member of this club is not
found.

The club's own member cards from Keys 1.5 and older are no longer shown in
the app. Codes members already have (printed cards, screenshots) still check
in; a later release removes them.

## Smart locks (Nuki)

Enter the club's Nuki API token (Nuki Web → API) in the Keys module settings,
then add each lock under *Smart locks* with its Nuki smartlock id and who may
open it: all members or one group. Every 15 minutes, and after each change,
Hubra brings Nuki in line:

- each member who may open the lock gets a keypad code of their own (6 digits,
  stored encrypted), shown under *My doors* on their account page;
- the code is removed when the membership ends, the member is suspended or
  leaves, or leaves the group;
- with *Open in the app*, members get an Open button; each opening is logged as
  a check-in at that door.

When Nuki cannot be reached, the member is shown in red and the next sync tries
again. Permission: **Manage smart locks** (`keys.locks.manage`).

## Install

Platform admins install it from the Plugin catalogue in manage
(official Marketplace, <https://plugins.hubra.club/index.json>, signed with
the Hubra project key). Clubs then switch it on under Einstellungen → Module.

## Develop

Clone this repository into `plugins/keys` of a Hubra checkout. Its tests
then run with Hubra's (`cd app/backend && pytest ../../plugins/keys`), and
`npm run build:plugin` in `app/frontend` builds its frontend. The workflow
does the same against Hubra's `main` on every push and pull request.

## Releasing

Bump `version` in `plugin.yaml`, add a `## <version>` section to
`CHANGELOG.md` and merge. Then tag the merged commit on main and push the tag:

```sh
git switch main && git pull
git tag v<version> && git push origin v<version>
```

The workflow tests the plugin and builds its frontend, the `plugin-signing`
job signs it after your approval, and only then is the GitHub release
`v<version>` published, with `keys-<version>.zip` and its `.sha256` attached. Files
listed in `.releaseignore` stay out of the zip. Releases are immutable, so a
published version never changes: fix a bad one with a new version.

Source: <https://github.com/hubra-app/hubra-plugin-keys>
