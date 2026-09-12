# Changelog

## Repository migration

- Project dipisahkan dari `MenkiPlugcore/plugin/plugins/MoonSignMenu` menjadi repository standalone `MenkiPlugcore/CdrMemberBook`.
- Plugin identity, Maven artifact, Java main class, dan Java package diganti menjadi CdrMemberBook.
- Permission prefix lama `moonsignmenu.*` tetap dipertahankan sementara untuk kompatibilitas server yang sudah berjalan.


## 1.3.1

- Member Book is now Bedrock-only by default.
- Reserved the configured hotbar slot for Member Book; default is slot `8` (far right).
- Added permanent hotbar enforcement so the book is restored if another plugin or inventory action removes it.
- Added move/swap/drag/offhand protection so Bedrock players cannot relocate the reserved book.
- Existing Java-player Member Books are automatically cleaned up when `member-book.bedrock-only: true`.
- If the reserved slot already contains an item, CdrMemberBook moves that item to a free storage slot before placing the book.
- Added `member-book.bedrock-only`, `permanent-hotbar`, `prevent-move`, and `enforce-interval-ticks` config options.

## 1.3.0

- Added Bedrock-native EssentialsX Home Manager (`type: homes`).
- Home Manager shows saved homes and the effective EssentialsX home limit, including unlimited home permission.
- Added click-only Set Home with manual home-name input, existing-home actions, teleport, delete, and delete confirmation.
- Added Bedrock-native transfer flow (`type: pay`): select an online player, type the amount manually, then confirm payment.
- Added Indonesian-friendly amount parsing such as `10000` and `10.000`.
- Added Bedrock-native AxTrade flow (`type: trade`) with Send, Accept, Deny, Toggle Requests, player picker, and Back navigation.
- Added configurable EssentialsX, pay, and AxTrade command templates under `integrations`.
- Added Java fallback commands for the new special button types.
- Added automatic v1.2 -> v1.3 config migration for the default Set Home, Transfer, and Barter buttons.
- Added EssentialsX API as a provided dependency and `Essentials` / `AxTrade` soft dependencies.

## 1.2.0

- Reworked the main menu into a fully config-driven button system.
- Buttons can now be added, removed, renamed, reordered, hidden, or disabled from `config.yml` without recompiling the plugin.
- Added configurable button types: `command`, `teleport`, `submenu`, and `close`.
- Added per-button Bedrock texture path, Java material, lore, permission, and player/console command executor.
- Added `%player%`, `%world%`, and `%uuid%` command placeholders.
- Added config-defined submenus with automatic Back navigation.
- Added Java menu pagination and player-selector pagination.
- Added `/menu reload` for live config reloads.
- Added migration from the v1.1 `menu-actions` and main Bedrock icon settings when upgrading an existing config.

## 1.1.0

- Added image icons to native Bedrock menu buttons using vanilla Bedrock texture paths.
- Removed emoji dependency from menu labels.
- Added Back navigation to the built-in teleport menu flow on Bedrock and Java.
- Reworked Bedrock teleport selection into icon-based SimpleForm pages so navigation stays consistent.
- Added automatic `MOONSIGN Member Book` item.
- Right-clicking Member Book opens the member menu without typing `/menu`.
- Member Book is restored when missing on join/respawn and can be configured to prevent dropping.
- Added configurable Bedrock icon paths and Member Book settings.
- Existing configs now receive new default keys automatically during upgrade.

## 1.0.0

- Added `/menu` member menu.
- Added native Bedrock forms through Floodgate.
- Added Java inventory GUI fallback.
- Added internal `/tpa`, `/tpahere`, `/tpaccept`, `/tpdeny`, and `/tptoggle` system.
- Added request expiration and anti-spam cooldown.
- Added persistent incoming-request toggle.
- Added optional cross-world blocking and cancellation on world change.
- Added configurable menu command actions and sound feedback.
