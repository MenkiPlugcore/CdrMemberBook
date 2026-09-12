# CdrMemberBook v1.9.8

Standalone Paper plugin by **CADERA** for a configurable Minecraft Java + Bedrock member menu.

## Target

- Paper 1.21.11
- Java 21
- Geyser + Floodgate for native Bedrock Forms
- Optional EssentialsX, AxTrade, PlaceholderAPI integrations

## Core Features

- `/menu` opens CdrMemberBook on Java and Bedrock.
- Polished Java inventory GUI with frame, pagination, player info, and Smart Menu filtering.
- Native Bedrock Forms through Floodgate.
- Config-driven main menu and submenus.
- Smart dependency detection: unavailable Bank/Shop/AH/etc. buttons are hidden automatically when their command/plugin is missing.
- Advanced action chains: command, console-command, message, sound, close, open-menu, and delay.
- Advanced conditions by permission, platform, world, online count, and PlaceholderAPI comparisons.
- Built-in TPA / TPAHere / accept / deny / toggle.
- Bedrock Home Manager through EssentialsX.
- Bedrock Pay and AxTrade click-first flows.
- Member Book modes, recovery, customization, and dynamic placeholders.
- Native Java + Bedrock report system and Staff Report Center.

## Report QoL & Audit — v1.9.5

Reports are stored in `plugins/CdrMemberBook/reports.yml` and remain compatible with reports created by older versions.

### Player report protection

```yaml
integrations:
  report:
    cooldown-seconds: 60
    duplicate-window-seconds: 300
    recent-limit: 10
```

`duplicate-window-seconds` prevents the same reporter from repeatedly reporting the same target during the configured window. Instead of creating another entry, CdrMemberBook returns the existing report ID.

### Staff Report Center

Staff permission:

```text
cdrmemberbook.staff.report
```

Java and Bedrock staff can view:

- OPEN reports
- RESOLVED reports
- all reports
- recent reports
- reporter/target details
- total reports involving a target
- latest staff notes
- audit/history metadata
- Resolve / Reopen / Delete actions

Bedrock has native search and staff-note Forms. Java staff now also has native Anvil search, category filters, paginated search/category results, and native staff-note input directly from Report Center. Admin commands remain available as a fallback.

### Report commands

```text
/cdrmemberbook reports [page] [open|resolved|all]
/cdrmemberbook reports search <reporter|target|any> <player> [open|resolved|all] [page]
/cdrmemberbook reports recent [limit]
/cdrmemberbook reports player <name>

/cdrmemberbook report view <id>
/cdrmemberbook report resolve <id>
/cdrmemberbook report reopen <id>
/cdrmemberbook report delete <id>
/cdrmemberbook report note <id> <catatan staff>
/cdrmemberbook report audit <id>
```

Audit entries are added for report creation, Resolve, Reopen, and staff notes. History and notes are bounded by config so `reports.yml` does not grow without limit.

```yaml
integrations:
  report:
    audit:
      max-history: 50
      max-notes: 20
      max-note-length: 240
    center:
      enabled: true
      page-size: 8
      allow-delete: true
      show-recent: true
      show-search: true
      detail-note-limit: 3
      detail-audit-limit: 5
```

## Smart Menu

Buttons can be hidden automatically when their backing feature is unavailable.

```yaml
menu:
  hide-buttons-without-permission: true
  hide-unavailable-buttons: true
  auto-detect-command-dependencies: true
```

Optional per-button dependency checks:

```yaml
bank:
  enabled: true
  name: Bank
  type: command
  command: bank
  requires-command: bank
  requires-plugins:
    - ExampleBankPlugin
```

Use this diagnostic command when a button unexpectedly appears or disappears:

```text
/cdrmemberbook menudebug <player> [menu]
```

## Advanced Actions

```yaml
shop:
  enabled: true
  name: Shop
  actions:
    - type: close
    - type: sound
      value: ENTITY_PLAYER_LEVELUP
    - type: command
      value: shop
    - type: message
      value: '&aShop dibuka.'
```

## Advanced Conditions

```yaml
conditions:
  platform: ANY
  worlds: [world]
  permissions: [server.shop]
  min-online: 1
  placeholders:
    - value: '%luckperms_primary_group%'
      operator: '!='
      compare: 'default'
```

## Member Book Modes

```yaml
member-book:
  mode: MOVABLE
  hotbar-slot: 8
  fixed-slot:
    return-delay-ticks: 40
```

Supported modes:

- `MOVABLE` — freely movable inside the player's inventory; recovery and protections remain active.
- `LOCKED_HOTBAR` — kept in the configured hotbar slot.
- `FIXED_SLOT_MOVABLE` — can be moved temporarily, then returns to its slot.
- `NORMAL` — behaves like an ordinary item with recovery/storage/drop protections disabled.

## Dynamic Member Book

Built-in placeholders:

```text
%player%
%uuid%
%world%
%ping%
%online%
```

PlaceholderAPI placeholders are supported when PlaceholderAPI and the required expansions are installed.

## Admin / Diagnostics

```text
/cdrmemberbook give <player>
/cdrmemberbook remove <player>
/cdrmemberbook fix <player>
/cdrmemberbook refresh <player>
/cdrmemberbook status <player>
/cdrmemberbook menudebug <player> [menu]
/cdrmemberbook health
/cdrmemberbook tutorialreset <player>
/cdrmemberbook tutorialshow <player>
```

## Build

```bash
mvn clean package
```

Output:

```text
target/CdrMemberBook-1.9.6.jar
```

## License

CdrMemberBook is distributed under the repository's **MENKIESTES SOFTWARE LICENSE v1.0**. MENKIESTES is created by **CADERA**. Third-party dependency licenses remain subject to their respective terms.

## Java Native Report Submit v1.9.6

Player Java sekarang memakai flow report bawaan yang sama dengan Bedrock dan tidak membutuhkan plugin `/report` eksternal. Klik tombol **Lapor** → pilih player online → ketik alasan pada UI Anvil native → cek halaman konfirmasi → kirim. Submit tetap memakai `ReportService`, sehingga cooldown, anti-duplicate v1.9.5, persistence `reports.yml`, staff notification, console hook, dan audit tetap konsisten lintas Java/Bedrock.

```yaml
integrations:
  report:
    java-submit:
      enabled: true
      reason-title: '&8Lapor • Alasan'
      reason-placeholder: 'Ketik alasan laporan...'
      reason-material: PAPER
```

Menutup Anvil dengan ESC membatalkan input tanpa menyimpan report. Target yang logout di tengah flow akan ditolak aman dan player dikembalikan ke picker.

## Report Categories & Evidence v1.9.7

Native Java + Bedrock report sekarang memakai flow kategori -> target -> alasan -> evidence opsional -> konfirmasi. Default kategori: CHEATING, GRIEFING, TOXIC, SCAM, BUG_ABUSE, OTHER. Evidence menerima teks atau link; link berskema non-http/https ditolak dan panjangnya dibatasi config. Report lama tetap kompatibel dan dibaca sebagai kategori OTHER tanpa evidence. Staff dapat memfilter kategori melalui `/cdrmemberbook reports category <category> [open|resolved|all] [page]`. Placeholder console hook baru: `%category%` dan `%evidence%`.
