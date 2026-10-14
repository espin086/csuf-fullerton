# Data fetch and credentials

## ADDED Requirements

### Requirement: FRED key from environment or secure store

The CLI SHALL read the FRED API key from `FRED_API_KEY` first, then the OS keychain, then a
`0600` credentials file, and SHALL never print or record the key.

#### Scenario: Init stores the key
- **WHEN** a user runs `csuf-fullerton init` and types a key at the hidden prompt
- **THEN** the key SHALL be stored in the keyring (or the `0600` file when no keyring backend
  exists) and SHALL NOT appear in the command output

#### Scenario: Environment wins
- **WHEN** `FRED_API_KEY` is set and a different key is in the keyring
- **THEN** the environment value SHALL be used

### Requirement: Recipes build an analysis CSV

`fetch` SHALL read a TOML recipe of FRED and IMF series with transforms, write one CSV on a
common date index, and write a sidecar JSON with each series' source, id, transform and
retrieval time.

#### Scenario: Transforms recorded
- **WHEN** a recipe series has `transform = "log"`
- **THEN** the CSV column SHALL be the natural log of the source values and the sidecar SHALL
  record `log`
