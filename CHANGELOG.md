# Changelog

## 1.11.0 - Admin Menu Editor

- Added `/cdrmemberbook menueditor` using the existing `cdrmemberbook.admin.memberbook` permission.
- Added native Java inventory + Anvil admin editor and native Bedrock Floodgate Forms editor.
- Added existing-menu selector and button create/edit/toggle/delete flows.
- Added editing for name, type, command, Java material, Bedrock icon, permission, order, lore and submenu target.
- Added dependency/condition editing for required command/plugins, platform, worlds, excluded worlds, extra permissions and min/max online.
- Added validation for button keys, material names, submenu references, numeric bounds and per-menu button safety cap.
- Existing action chains and PlaceholderAPI condition maps remain untouched by unrelated edits.
- Changes save directly to config.yml and menu validation runs immediately without restart.
- Config migrated to version 27.


## 1.10.0 - Player Preferences

- Added lightweight persistent `preferences.yml` storage per player UUID.
- Added native Java and Bedrock Settings UI with sounds, tutorial, TPA status notification, staff report notification, menu mode and default-menu controls.
- Added FULL / COMPACT menu presentation preference.
- `/menu` and Member Book now honor each player's selected default menu.
- Wired sound preferences into built-in teleport sounds and advanced menu sound actions.
- Wired tutorial preference into automatic first-join tutorial delivery.
- Wired report notification preference into staff report chat alerts.
- Added safe TPA status-notification preference while keeping incoming request and accept/deny controls visible.
- Added reset-to-server-defaults and config migration v26.

## 1.9.8 - Report Center Java QoL

- Added native Java Report Center search selector for reporter, target, or ANY lookup.
- Added Anvil-based Java search input without requiring admin commands or chat interception.
- Added native Java category filter with per-category report counts.
- Added paginated Java custom result lists for Recent, Search, and Category views.
- Preserved Search/Category/Recent context when opening report details, resolving/reopening/deleting, or returning to results.
- Added native Java Staff Note input via Anvil with max-length validation and audit persistence.
- Added category labels to Java report list rows and kept all report permission checks on every callback.
- Config migrated to version 25 with Java Report Center search/note UI settings.

## 1.9.7 - Report Categories & Evidence

- Added configurable report categories shared by Java and Bedrock native submit flows.
- Added optional evidence text/link with length and URL-scheme validation.
- Persisted category/evidence in reports.yml while keeping old reports backward compatible as OTHER/no evidence.
- Added category/evidence to staff notifications, console hook placeholders, Java/Bedrock details, audit context and admin output.
- Added `/cdrmemberbook reports category <category> [open|resolved|all] [page]`.
- Java flow is now category -> target -> reason anvil -> evidence anvil -> confirmation.
- Bedrock flow is now category -> target -> reason -> evidence -> confirmation.
- Config migrated to version 24.

## 1.9.6 - Java Native Report Submit

- Added fully native Java report submission without requiring an external `/report` plugin.
- Added Java inventory target picker with pagination and self-target exclusion.
- Added native Anvil reason input, configurable title/placeholder/material, min/max validation and no chat interception.
- Added Java confirmation GUI with target head, wrapped reason preview, Edit, Cancel and Send actions.
- Java and Bedrock submissions now share the same `ReportService`, cooldown, anti-duplicate protection, persistence, staff notifications and audit pipeline.
- Added config migration v23 and Java-native report availability detection.

## 1.9.5 - Report QoL & Audit

- Added anti-duplicate reporter-to-target window with existing report ID feedback.
- Added reporter/target/ANY search, recent reports, per-player report statistics and target report counts.
- Added persistent staff notes and bounded audit history for CREATE/RESOLVE/REOPEN/NOTE actions.
- Added Bedrock Report Center search, recent reports and native staff-note input.
- Added Java recent reports plus richer report detail with counts, notes and audit metadata.
- Added admin report `note` and `audit` actions plus `reports search`, `recent`, and `player` lookup commands.


## 1.9.4 - Java Menu UI & Report Center

- Reworked `/menu` on Java into a polished fixed 6-row inventory layout with frame decorations and centered content slots.
- Added Java menu player info, click hints, consistent Previous/Back/Next navigation and cleaner player picker/TP screens.
- Added configurable Java GUI filler/accent materials without requiring a resource pack.
- Added native Java Staff Report Center with OPEN / RESOLVED / ALL lists, pagination and report details.
- Added Java Resolve, Reopen and Delete confirmations with permission rechecks on every report action.
- Report Center is now available to both Java and Bedrock staff through the same `cdrmemberbook.staff.report` permission.
- Config migrated to version 21; existing Bedrock-only Report Center button is migrated to platform `ANY`.


## 1.9.3 - Bedrock Staff Report Center

- Added native Bedrock `Report Center` for staff permission `cdrmemberbook.staff.report`.
- Added OPEN / RESOLVED / ALL filters with pagination and refresh.
- Added report detail view with reporter, target, reason, timestamp, location and resolution metadata.
- Added native Resolve, Reopen and Delete actions with confirmation forms.
- Added `report-center` menu button type and default Bedrock-only staff button.
- Kept Java Report Center hidden for a dedicated follow-up Java UI update.


## 1.9.2 - Production Hardening

- Added guarded/cancellable menu action chains with anti-spam cooldown and safety caps.
- Made `menu.actions.enabled` authoritative at runtime.
- Added fail-safe and resource limits for advanced menu conditions.
- Hardened report persistence so success is only returned after a successful disk save.
- Sanitized report reasons and hardened report admin mutation feedback.
- Added `/cdrmemberbook health` production diagnostics.


## 1.9.1 - Menu Conditions Advanced

- Added per-button platform, world, extra permission and online-count conditions.
- Added PlaceholderAPI comparisons for rank/economy/level/custom plugin state.
- Menu debug reports the exact condition that hides an unavailable button.


## 1.9.0 - Advanced Menu Actions

- Buttons can execute ordered action chains instead of one command.
- Action types: command, console-command, message, sound, close, open-menu and delay.
- Action chains keep legacy single-command buttons fully compatible.


## 1.8.4 - Report Management

- Added report status lifecycle: OPEN/RESOLVED with resolver and timestamp.
- Added admin list/view/resolve/reopen/delete commands.
- Existing report files remain readable; entries without status are treated as OPEN.


## 1.8.3 - Smart Menu Stability

- Added `/cdrmemberbook menudebug <player> [menu]` with explicit visibility/dependency reasons.
- Added startup/reload menu configuration validation and warnings.
- Dead buttons now expose structured availability codes for debugging.


## 1.8.2 - Full CdrMemberBook Rebrand

- Removed remaining server-specific branding and legacy permission aliases from the current plugin tree.
- Official permission namespace is now only `cdrmemberbook.*`.
- Added config migration v14 to rewrite old branding values in existing server configs.
- Updated startup version and public documentation for the standalone plugin identity.

## 1.8.1 - Rebrand Cleanup

- Replaced public-facing server-specific branding with CdrMemberBook.
- Changed default permission namespace to `cdrmemberbook.*`.
- Updated default prefix, Member Book name/lore, tutorial title, menu title and item-model namespace example.

## 1.8.0 - Smart Menu Conditions & Native Report

- Menu buttons can auto-hide when their command/dependency is unavailable.
- Generic command buttons auto-detect their root command, so Bank/Shop/AH/etc do not appear when no provider exists.
- Homes, Pay and AxTrade buttons validate their integrations before being shown.
- Added optional per-button `requires-plugins`, `requires-command`, and `auto-detect-command`.
- Added native Bedrock report flow with player picker, reason input, confirmation, cooldown, staff notification and persistent `reports.yml`.
- Java keeps `/report` as a fallback only when that command actually exists.

## 1.7.0 - First Join Tutorial

- Added native three-step Bedrock first-join tutorial.
- Tutorial completion/eligibility persists per UUID in `tutorial-data.yml`.
- Existing players are not shown the tutorial by default.
- Closing before completion keeps first-join players eligible for the next login.
- Added `/cdrmemberbook tutorialreset <player>` and `/cdrmemberbook tutorialshow <player>`.

## 1.6.1 - Book Modes Stability

- Added `/cdrmemberbook status <player>` diagnostics.
- Added startup/reload validation for invalid mode, hotbar slot and fixed-slot delay.
- Hardened Book Modes observability without changing default MOVABLE behavior.

## Repository migration

- Project dipisahkan dari `MenkiPlugcore/plugin/plugins/CdrMemberBookMenu` menjadi repository standalone `MenkiPlugcore/CdrMemberBook`.
- Plugin identity, Maven artifact, Java main class, dan Java package diganti menjadi CdrMemberBook.
- Permission prefix lama `cdrmemberbook.*` tetap dipertahankan sementara untuk kompatibilitas server yang sudah berjalan.

## 1.6.0 — Book Modes

- Added `member-book.mode` with four modes: `MOVABLE`, `LOCKED_HOTBAR`, `FIXED_SLOT_MOVABLE`, and `NORMAL`.
- `MOVABLE` preserves the current production behavior: free movement inside the player's own inventory while Safety & Recovery and external-storage protection remain active.
- `LOCKED_HOTBAR` keeps one Member Book in `hotbar-slot`, blocks direct movement of the book, and continuously restores the configured slot.
- `FIXED_SLOT_MOVABLE` allows temporary internal movement but returns the Member Book to `hotbar-slot` after `fixed-slot.return-delay-ticks` (40 ticks by default).
- `NORMAL` behaves like a regular item: no periodic recovery, no duplicate cleanup, no anti-drop, no external-storage protection, no hopper/dispenser protection, and no death-drop removal. Right-click still opens the menu.
- `NORMAL` can still honor `give-on-join`; because the plugin intentionally does not search arbitrary containers in this mode, servers that want a fully manual normal item should set `give-on-join: false` and use the admin give command.
- Legacy `permanent-hotbar: true` automatically migrates to `LOCKED_HOTBAR`; other existing installations migrate to `MOVABLE` so current production behavior is preserved.
- Added mode name logging on plugin startup and safe fallback to `MOVABLE` for an invalid mode value.
- Config migration v10 -> v11 adds mode and fixed-slot defaults.
- Version bumped to `1.6.0`.

## 1.5.3 — Home Manager Advanced

- Added advanced per-preset metadata under `integrations.essentials-home.preset-details`.
- Each preset now supports `enabled`, `display-name`, Bedrock `icon`, and optional `permission`.
- Existing legacy `presets: [rumah, base, ...]` remains the canonical order/name list and stays backward compatible.
- Set Home buttons use configured display names/icons while commands continue to use the canonical EssentialsX home name.
- Teleport Home and Hapus Home can also show the configured display name/icon for matching owned homes without changing the underlying home id.
- Presets without permission are hidden by default; `hide-locked-presets: false` shows them as `Terkunci` instead.
- Restricted preset names cannot be bypassed through `Nama Custom`; permission is revalidated centrally before Set/Overwrite.
- Preset permission only controls Set/Overwrite. Existing owned homes remain available for teleport/delete to avoid locking old player data.
- Added automatic default icons for common preset names (`rumah/base`, `farm`, `tambang`, `shop`).
- Config migration v9 -> v10 adds advanced metadata without removing existing preset lists.
- Version bumped to `1.5.3`.

## 1.5.2 — Bedrock Menu QoL

- Added configurable Member Book anti-double-open cooldown; default is 20 ticks (1 second) to prevent duplicate Bedrock forms from rapid/right-hand-offhand interactions.
- Home Manager now includes an optional `Refresh Home` button and displays the current home count directly on Teleport/Delete buttons.
- Empty home states are explicit (`BELUM ADA`) instead of looking like a broken picker.
- EssentialsX home lists are sorted alphabetically by default for Teleport and Delete pickers; sorting can be disabled in config.
- Added success feedback after Set/Overwrite Home and Delete Home actions.
- Existing menu permission filtering remains active through `menu.hide-buttons-without-permission: true`; no duplicate permission layer was introduced.
- Added `member-book.open-cooldown-ticks`, `integrations.essentials-home.sort-alphabetically`, and `show-refresh-button`.
- Added configurable `home-list-refreshed`, `home-set-success`, and `home-delete-success` messages.
- Config migration v8 -> v9 adds the new QoL defaults without changing existing home presets.
- Version bumped to `1.5.2`.

## 1.5.1 — Home Picker QoL

- Reworked the Bedrock Home Manager into a fully click-first flow: `Teleport Home`, `Set Home`, `Hapus Home`, and `Kembali`.
- `Teleport Home` now shows the player's actual EssentialsX home names as buttons and teleports immediately after selection; players never need to type `/home`.
- `Set Home` now shows configurable preset home-name buttons; default presets are `rumah`, `base`, `farm`, `tambang`, and `shop`.
- Existing preset homes are labeled as overwrite actions and require confirmation before the location is replaced.
- Added optional `Nama Custom` input for servers that still want arbitrary home names without exposing commands.
- `Hapus Home` now has its own home picker and delete confirmation flow.
- Home limits and unlimited-home permissions continue to use EssentialsX directly.
- Added `integrations.essentials-home.presets` and `allow-custom-name`.
- Config migration v7 -> v8 automatically adds the Home Picker defaults.
- Version bumped to `1.5.1`.

## 1.5.0 — Dynamic Member Book

- Added optional PlaceholderAPI integration for dynamic Member Book name and lore.
- Added built-in placeholders `%player%`, `%uuid%`, `%world%`, `%ping%`, and `%online%` that work even without PlaceholderAPI.
- Added lightweight scheduled dynamic refresh; default interval is 200 ticks (10 seconds), with a 40-tick internal minimum.
- Added `member-book.dynamic.enabled`, `placeholderapi`, `built-in-placeholders`, `refresh-interval-ticks`, `refresh-on-join`, and `refresh-on-world-change`.
- PlaceholderAPI is a soft dependency; CdrMemberBook remains functional when it is not installed.
- Dynamic refresh only updates eligible players that already own a Member Book and never bypasses Bedrock-only eligibility or admin recovery suppression.
- Added `/cdrmemberbook refresh <player>` for manual placeholder/lore refresh.
- Existing Safety & Recovery and Book Customization PDC identity/protections remain intact after every dynamic refresh.
- Config migration v6 -> v7 automatically adds dynamic defaults without changing existing name/lore text.
- Added PlaceholderAPI 2.12.3 as a provided Maven dependency; it is not bundled into the plugin jar.
- Version bumped to `1.5.0`.

## 1.4.1 — Book Customization

- Added configurable `custom-model-data` for legacy/custom resource-pack item models.
- Added Minecraft 1.21.4+ `item-model` support using namespaced item model keys such as `cdrmemberbook:member_book`.
- Added tri-state `enchant-glint`: `true`, `false`, or `default`.
- Added optional `hide-tooltip`, `hide-attributes`, and `hide-additional-tooltip` controls.
- Added arbitrary Bukkit `item-flags` list support for advanced item presentation.
- Existing `material`, `name`, and `lore` settings remain fully configurable and backward compatible.
- Added `refresh-existing`; online Bedrock players' existing Member Books can be restyled automatically on join/reload without deleting and re-giving the book.
- `/cdrmemberbook give` and `/cdrmemberbook fix` now refresh the appearance of an existing book before recovery/repair.
- Customization never removes the Member Book PDC identity marker, so Safety & Recovery protections continue to work after restyling.
- Config migration v5 -> v6 automatically adds customization defaults without changing the current visual appearance.
- Version bumped to `1.4.1`.

## 1.4.0 — Member Book Safety & Recovery

- Added lightweight periodic recovery for eligible Bedrock/Floodgate players; default interval is 100 ticks (5 seconds).
- Member Book is restored if it disappears because of `/clear`, another plugin, or an inventory desync/bug.
- Recovery checks player inventory, cursor state, and the currently open external inventory before creating a new copy, preventing cursor-related duplication.
- Added duplicate cleanup for Member Books found in player inventory/cursor.
- If a marked Member Book somehow reaches an open chest, ender chest, PlayerVaults/PV, shulker, or plugin inventory, it is recovered back to the player when possible.
- Added recovery checks after join, respawn, world change, inventory open/close, relevant click/drag operations, and plugin config reload.
- Added protection against hopper/container transfer (`InventoryMoveItemEvent`), hopper pickup, dispenser use, and illicit dropped Member Book pickup.
- Member Book remains Bedrock-only by default; Java players do not receive it and stale Java copies are cleaned from their own inventory/cursor.
- Added admin command `/cdrmemberbook give <player>` to ensure an eligible player owns a Member Book.
- Added admin command `/cdrmemberbook remove <player>` to remove visible copies and suppress auto-recovery until relog or `give/fix`.
- Added admin command `/cdrmemberbook fix <player>` to clean duplicates, recover visible external copies, and restore one valid book.
- Added permission `cdrmemberbook.admin.memberbook` (default: OP).
- Added `member-book.recovery.enabled`, `interval-ticks`, `recover-on-world-change`, `recover-from-open-container`, and `remove-duplicates` settings.
- `/menu reload` now restarts the Member Book recovery task so recovery config changes apply without a server restart.
- Config migration v4 -> v5 automatically enables the new recovery defaults.
- Version bumped to `1.4.0`.

## 1.3.2

- Member Book sekarang bebas dipindah-pindah di inventory dan hotbar player sendiri.
- Default `permanent-hotbar` diubah menjadi `false`; slot `hotbar-slot` hanya dipakai sebagai slot awal pemberian buku.
- Ditambahkan `member-book.prevent-external-storage` dengan default `true`.
- Member Book tidak dapat dimasukkan ke chest, ender chest, shulker, PlayerVaults/PV, plugin GUI, crafting/result inventory, atau inventory eksternal lainnya.
- Proteksi mencakup normal click, shift-click, inventory drag, hotbar number-key swap, dan offhand swap ke inventory eksternal.
- Member Book tetap dapat dipindahkan antar-slot inventory milik player, termasuk hotbar dan offhand.
- Right-click Member Book dari main hand maupun offhand tetap membuka menu.
- Periodic hotbar enforcement hanya dijalankan jika mode legacy `permanent-hotbar: true` digunakan, mencegah duplikasi saat buku sedang berada di cursor.
- Config migration v3 -> v4 otomatis menonaktifkan `permanent-hotbar`/`prevent-move` dan mengaktifkan `prevent-external-storage`.
- Version bumped to `1.3.2`.

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
- Added automatic `CdrMemberBook Member Book` item.
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
