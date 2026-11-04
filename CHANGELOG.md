# Changelog

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
