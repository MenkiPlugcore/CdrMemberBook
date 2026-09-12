# CdrMemberBook v1.8.4

Standalone Paper plugin by **CADERA** untuk member menu Minecraft Java + Bedrock. Project ini dipisahkan dari monorepo `MenkiPlugcore/plugin` agar release, maintenance, issue, dan update berikutnya dapat dikelola langsung dari repository ini.

## Target

- Paper 1.21.11
- Java 21
- Geyser + Floodgate untuk native Bedrock UI
- EssentialsX untuk Home Manager
- AxTrade untuk flow Barter

## Fitur utama

- `/menu` atau klik kanan Member Book untuk membuka menu.
- Native Bedrock Forms melalui Floodgate.
- Java inventory GUI fallback.
- Built-in TPA / TPAHere / accept / deny / toggle.
- Menu utama dan submenu config-driven.
- Tombol `Kembali` pada submenu internal.
- Tambah/hapus/edit/reorder tombol tanpa compile ulang.
- Button types: `command`, `teleport`, `homes`, `pay`, `trade`, `submenu`, `close`.
- `/menu reload` untuk menerapkan perubahan config tanpa restart.
- Member Book Bedrock-only secara default.
- Member Book bebas dipindah di inventory/hotbar/offhand player sendiri.
- Member Book tidak dapat dimasukkan ke chest, ender chest, shulker, PlayerVaults/PV, plugin GUI, atau inventory eksternal lain.
- Shift-click, drag, hotbar-number swap, offhand swap, hopper/container transfer, hopper pickup, dan dispenser ikut diproteksi.
- Member Book tetap tidak dapat dibuang jika `prevent-drop: true`.
- Safety recovery otomatis memulihkan buku yang hilang dan membersihkan duplikat.

## Book Modes v1.8.2

Behavior Member Book sekarang dapat dipilih melalui `member-book.mode` tanpa compile ulang:

```yaml
member-book:
  mode: MOVABLE
  hotbar-slot: 8
  enforce-interval-ticks: 20
  fixed-slot:
    return-delay-ticks: 40
```

| Mode | Behavior |
|---|---|
| `MOVABLE` | Default production. Buku bebas dipindah di inventory sendiri; anti-drop, external-storage protection, dan Safety & Recovery tetap aktif. |
| `LOCKED_HOTBAR` | Buku dijaga di `hotbar-slot` dan perpindahan langsung diblok. Cocok untuk server yang ingin tombol menu permanen. |
| `FIXED_SLOT_MOVABLE` | Player boleh memindahkan buku, tetapi setelah delay buku otomatis dikembalikan ke `hotbar-slot`. |
| `NORMAL` | Member Book menjadi item biasa. Bisa dibuang/disimpan/dipindah normal; tidak ada recovery atau slot enforcement. Right-click tetap membuka menu. |

`NORMAL` tetap dapat memakai `give-on-join: true`, tetapi plugin sengaja tidak melacak buku di chest/container pada mode ini. Untuk item normal yang sepenuhnya manual gunakan `give-on-join: false`, lalu berikan melalui `/cdrmemberbook give <player>`.

Config lama tetap aman: `permanent-hotbar: true` dimigrasikan menjadi `LOCKED_HOTBAR`, sedangkan instalasi lainnya menjadi `MOVABLE`.

## Dynamic Member Book

`v1.5.0` mendukung placeholder pada `member-book.name` dan setiap baris `member-book.lore`. Placeholder bawaan `%player%`, `%uuid%`, `%world%`, `%ping%`, dan `%online%` bekerja tanpa dependency tambahan. Jika PlaceholderAPI terpasang, placeholder dari expansion lain juga dapat dipakai.

```yaml
member-book:
  name: '&d&lCdrMemberBook &f%player%'
  lore:
    - '&7Rank: &f%luckperms_prefix%'
    - '&7Balance: &a%vault_eco_balance_formatted%'
    - '&7Ping: &f%ping%ms'
    - '&7Online: &f%online%'
  dynamic:
    enabled: true
    placeholderapi: true
    built-in-placeholders: true
    refresh-interval-ticks: 200
    refresh-on-join: true
    refresh-on-world-change: true
```

PlaceholderAPI bersifat optional/soft dependency. Expansion seperti LuckPerms/Vault tetap harus tersedia agar placeholder masing-masing dapat di-resolve. Gunakan `/cdrmemberbook refresh <player>` untuk refresh manual.

## Book Customization

`v1.4.1` menambahkan kontrol tampilan item tanpa mengubah identitas/proteksi Member Book.

```yaml
member-book:
  material: BOOK
  name: '&d&lCdrMemberBook &fMember Book'
  lore:
    - '&7Klik kanan untuk membuka Menu Member.'
  customization:
    custom-model-data: 0
    item-model: ''
    enchant-glint: default
    hide-tooltip: false
    hide-attributes: false
    hide-additional-tooltip: false
    item-flags: []
    refresh-existing: true
```

`item-model` memakai format `namespace:key` dan ditujukan untuk sistem item model Minecraft 1.21.4+. `custom-model-data` tetap tersedia untuk kompatibilitas legacy. Untuk client Bedrock melalui Geyser, model/tekstur custom memerlukan Geyser custom item mapping dan Bedrock resource pack; plugin hanya menetapkan komponen item Java yang menjadi basis mapping.

`/menu reload` akan menerapkan konfigurasi tampilan terbaru ke Member Book player online jika `refresh-existing: true`.

## Member Book Safety & Recovery

Default v1.4.0 menggunakan mode movable + recovery ringan:

```yaml
member-book:
  enabled: true
  bedrock-only: true
  give-on-join: true
  permanent-hotbar: false
  prevent-move: false
  prevent-external-storage: true
  hotbar-slot: 8
  prevent-drop: true

  recovery:
    enabled: true
    interval-ticks: 100
    recover-on-world-change: true
    recover-from-open-container: true
    remove-duplicates: true
```

`hotbar-slot` hanya menjadi slot awal ketika buku pertama kali diberikan. Setelah itu player bebas memindahkan buku ke slot inventory miliknya sendiri.

Recovery berjalan tiap 100 ticks (5 detik) secara default. Sebelum membuat buku baru, CdrMemberBook memeriksa inventory, cursor, dan container yang sedang dibuka sehingga item yang sedang dipegang mouse tidak dianggap hilang dan tidak menghasilkan duplikasi.

Jika Member Book hilang karena `/clear`, plugin lain, desync, atau bug inventory, plugin akan membuat/memulihkan satu copy untuk player Bedrock yang eligible. Jika copy bertanda Member Book lolos ke container yang sedang dibuka, plugin mencoba menariknya kembali ke inventory player.

Java player tetap tidak menerima Member Book saat `bedrock-only: true`. Java tetap bisa menggunakan `/menu` dan Java inventory GUI fallback.

## Admin Recovery Commands

Permission: `cdrmemberbook.admin.memberbook` (default OP).

| Command | Fungsi |
|---|---|
| `/cdrmemberbook give <player>` | Pastikan player Bedrock memiliki satu Member Book |
| `/cdrmemberbook remove <player>` | Hapus copy yang terlihat dan tahan auto-recovery sampai relog atau `give/fix` |
| `/cdrmemberbook fix <player>` | Bersihkan duplikat, recover copy eksternal yang terlihat, lalu pastikan satu buku valid |

## Bedrock Home Manager

Gunakan `type: homes`. CdrMemberBook membaca data home dan limit langsung dari EssentialsX. Flow Bedrock bersifat click-first: `Teleport Home`, `Set Home`, `Hapus Home`, dan `Refresh Home`. Daftar home aktual otomatis muncul sebagai tombol, diurutkan alfabetis secara default, dan tidak mengharuskan player mengetik `/home`.

`v1.5.2` menambahkan anti-double-open Member Book default 20 ticks (1 detik), state `BELUM ADA` untuk player tanpa home, serta feedback sukses setelah set/overwrite dan delete home.

`v1.5.3` menambahkan metadata advanced per preset: display name, icon Bedrock, enable/disable, dan permission. Permission preset hanya membatasi Set/Timpa; home yang sudah dimiliki tetap dapat diteleport atau dihapus.

```yaml
integrations:
  essentials-home:
    set-command: 'sethome %home%'
    teleport-command: 'home %home%'
    delete-command: 'delhome %home%'
    presets:
      - rumah
      - base
      - farm
      - tambang
      - shop
    allow-custom-name: true
    hide-locked-presets: true
    use-display-names-on-owned-homes: true
    preset-details:
      rumah:
        enabled: true
        display-name: 'Rumah'
        icon: textures/items/bed_red
        permission: ''
      farm:
        enabled: true
        display-name: 'Farm'
        icon: textures/items/wheat
        permission: 'moonsign.home.farm'
```

`Teleport Home` menampilkan home yang benar-benar dimiliki player. `Set Home` menampilkan tombol preset; preset yang sudah ada akan meminta konfirmasi sebelum ditimpa. `Nama Custom` dapat dimatikan dengan `allow-custom-name: false` jika server ingin 100% tombol tanpa input teks. Jika sebuah preset diberi `permission`, player tanpa permission tidak dapat Set/Timpa nama tersebut bahkan melalui input custom.

```yaml
sethome:
  enabled: true
  name: Home
  type: homes
  command: homes
  icon: textures/items/bed_red
  java-material: RED_BED
```

## Bedrock Transfer / Pay

Gunakan `type: pay`. Player Bedrock memilih player online, memasukkan nominal, lalu mengonfirmasi pembayaran.

```yaml
integrations:
  pay:
    command: 'pay %target% %amount%'
```

## Bedrock AxTrade / Barter

Gunakan `type: trade`. Flow menyediakan Send, Accept, Deny, Toggle Requests, player picker, dan Back navigation.

```yaml
integrations:
  axtrade:
    send-command: 'axtrade %target%'
    accept-command: 'axtrade accept %target%'
    deny-command: 'axtrade deny %target%'
    toggle-command: 'axtrade toggle'
```

## Command

| Command | Fungsi |
|---|---|
| `/menu` | Buka Menu Member |
| `/menu reload` | Reload `config.yml` dan restart recovery task tanpa restart server |
| `/tpa <player>` | Minta teleport ke player |
| `/tpahere <player>` | Minta player teleport ke kamu |
| `/tpaccept` | Terima request |
| `/tpdeny` | Tolak request |
| `/tptoggle` | Matikan/aktifkan incoming request |

## Build

```bash
mvn clean package
```

Output:

```text
target/CdrMemberBook-1.6.0.jar
```

## Migration

Source awal project ini berasal dari `plugins/CdrMemberBookMenu` pada repository `MenkiPlugcore/plugin`. Mulai sekarang pengembangan CdrMemberBook dilakukan di repository standalone ini.

Saat upgrade dari config v4 ke v5, plugin otomatis menambahkan dan mengaktifkan default recovery `v1.4.0` tanpa perlu menghapus `config.yml` lama.


## Book Modes Stability v1.8.2

Use `/cdrmemberbook status <player>` to inspect active mode, visible copies, reserved slot, recovery suppression, external/drop protection and dynamic refresh state. Invalid Book Mode config values safely fall back to `MOVABLE` and produce a startup/reload warning.


## First Join Tutorial v1.8.2

New Bedrock players receive a native three-step tutorial after join. Completion is persisted in `plugins/CdrMemberBook/tutorial-data.yml`. Existing players are skipped by default (`tutorial.show-to-existing-unseen: false`). Admins can test/reset with `/cdrmemberbook tutorialshow <player>` and `/cdrmemberbook tutorialreset <player>`.


## Smart Menu Conditions v1.8.2

Buttons are hidden automatically when their backing command or integration is unavailable. Command buttons auto-detect the root command, and optional `requires-plugins`, `requires-command`, and `auto-detect-command` fields are supported per button. Bedrock `type: report` uses CdrMemberBook's native report flow and stores reports in `plugins/CdrMemberBook/reports.yml`.


## Rebrand Cleanup v1.8.2

All public-facing branding now uses **CdrMemberBook**. Default permission nodes use `cdrmemberbook.*`. Legacy `cdrmemberbook.*` aliases remain only for backward compatibility with existing permission setups.


## Full CdrMemberBook Branding v1.8.2

CdrMemberBook is now fully server-agnostic. Public UI, default config, permission nodes, item/model namespace examples, tutorial, report system and documentation use only the **CdrMemberBook** identity. Official permissions use `cdrmemberbook.*`.
