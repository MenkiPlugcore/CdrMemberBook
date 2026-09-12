# CdrMemberBook v1.3.2

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
- Member Book Bedrock-only dapat diatur lewat `config.yml`.
- Member Book bebas dipindah di inventory/hotbar player sendiri.
- Member Book tidak dapat dimasukkan ke chest, ender chest, shulker, PlayerVaults/PV, plugin GUI, atau inventory eksternal lain.
- Shift-click, drag, hotbar-number swap, dan offhand swap ke inventory eksternal ikut diproteksi.
- Member Book tetap tidak dapat dibuang jika `prevent-drop: true`.

## Member Book Storage Protection

Default v1.3.2 menggunakan mode movable:

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
```

`hotbar-slot` hanya menjadi slot awal ketika buku pertama kali diberikan. Setelah itu player bebas memindahkan buku ke slot inventory miliknya sendiri.

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
| `/menu reload` | Reload `config.yml` tanpa restart |
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
target/CdrMemberBook-1.3.2.jar
```

## Migration

Source awal project ini berasal dari `plugins/MoonSignMenu` pada repository `MenkiPlugcore/plugin`. Mulai sekarang pengembangan CdrMemberBook dilakukan di repository standalone ini.

Saat upgrade dari config v3 ke v4, plugin otomatis mengubah Member Book ke mode movable dan mengaktifkan `prevent-external-storage`.
