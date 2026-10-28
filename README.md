# Keys

A plugin for [Hubra](https://hubra.club). Physical keys, cards and fobs: who holds which, with a handover log. Members see their keys on their account page.

**Version** 1.0.0 · **Works with** Hubra >=0.1,<1 · **Plugin id** `keys`

## Install

Platform admins install it from the plugin catalogue in the manager portal
(official Marketplace, <https://plugins.hubra.club/index.json>, signed with
the Hubra project key). Clubs then switch it on under Einstellungen → Module
& Plugins.

## Develop

Clone this repository into `plugins/keys` of a Hubra checkout. Its tests
then run with Hubra's (`cd app/backend && pytest ../../plugins/keys`), and
`npm run build:plugin` in `app/frontend` builds its frontend. The workflow
does the same against Hubra's `main` on every push and pull request.

## Releasing

Bump `version` in `plugin.yaml`, add a `## <version>` section to
`CHANGELOG.md`, commit, then publish a GitHub release tagged `v<version>`
(web UI, or `gh release create v<version> --target main --notes ""`). The
workflow tests the plugin, builds its frontend, signs it with the
`HUBRA_SIGNING_KEY` secret and attaches `keys-<version>.zip` to the
release. Files listed in `.releaseignore` stay out of the zip.

Source: <https://github.com/hubra-app/hubra-plugin-keys>
