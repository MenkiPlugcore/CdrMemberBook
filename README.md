# CdrMemberBook v1.5.0

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

## Dynamic Member Book

`v1.5.0` mendukung placeholder pada `member-book.name` dan setiap baris `member-book.lore`. Placeholder bawaan `%player%`, `%uuid%`, `%world%`, `%ping%`, dan `%online%` bekerja tanpa dependency tambahan. Jika PlaceholderAPI terpasang, placeholder dari expansion lain juga dapat dipakai.

```yaml
member-book:
  name: '&d&lMOONSIGN &f%player%'
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
  name: '&d&lMOONSIGN &fMember Book'
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

Permission: `moonsignmenu.admin.memberbook` (default OP).

| Command | Fungsi |
|---|---|
| `/cdrmemberbook give <player>` | Pastikan player Bedrock memiliki satu Member Book |
| `/cdrmemberbook remove <player>` | Hapus copy yang terlihat dan tahan auto-recovery sampai relog atau `give/fix` |
| `/cdrmemberbook fix <player>` | Bersihkan duplikat, recover copy eksternal yang terlihat, lalu pastikan satu buku valid |

## Bedrock Home Manager

Gunakan `type: homes`. CdrMemberBook membaca data home dan limit langsung dari EssentialsX, lalu menyediakan daftar home, set home baru, teleport, hapus dengan konfirmasi, serta dukungan home unlimited.

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
target/CdrMemberBook-1.5.0.jar
```

## Migration

Source awal project ini berasal dari `plugins/MoonSignMenu` pada repository `MenkiPlugcore/plugin`. Mulai sekarang pengembangan CdrMemberBook dilakukan di repository standalone ini.

Saat upgrade dari config v4 ke v5, plugin otomatis menambahkan dan mengaktifkan default recovery `v1.4.0` tanpa perlu menghapus `config.yml` lama.
