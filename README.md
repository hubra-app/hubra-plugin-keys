# Keys

[![Test and release](https://github.com/hubra-app/hubra-plugin-keys/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/hubra-app/hubra-plugin-keys/actions/workflows/release.yml?query=branch%3Amain) [![License: all rights reserved](https://img.shields.io/badge/license-all%20rights%20reserved-lightgrey)](LICENSE)

A plugin for [Hubra](https://hubra.club). Physical keys, cards and fobs: who holds which, with a handover log. Members see their keys on their account page.

**Version** 1.3.0 · **Works with** Hubra >=0.2,<1 · **Plugin id** `keys`

## Member cards and check-in

Every member has a member card on their account page: a QR code with a link
to the club's check-in screen. Whoever has the right **Check members in with
their member card** (`keys.checkins.create`) opens *Check-in* and scans:

- with the phone camera: the link opens the check-in screen, shows who it is,
  and one tap checks them in;
- with a USB or Bluetooth QR scanner, which types the code into the field;
- in Chrome on Android, with the camera button on the screen itself.

At an event of the day, a check-in marks the member present on the event's
attendance list (an "excused" becomes "present"). Without an event it logs who
came in and where (door, open workshop). The same card twice counts once.
Suspended members and members who left are refused; an ended membership is
shown in red. A member can make a new code, which ends the old one, including
screenshots of it.

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
