from pathlib import Path
import re

root = Path('.')

# BedrockFormService.java
p = root / 'src/main/java/id/cadera/memberbook/form/BedrockFormService.java'
s = p.read_text()
pattern = re.compile(r'''    private void showHomesMenu\(Player player, String returnMenuId, String fallbackCommand\) \{.*?^    private void showPayPlayerSelect\(Player player, String returnMenuId\) \{''', re.S | re.M)
replacement = '''    private void showHomesMenu(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            plugin.message(player, "home-integration-unavailable");
            if (fallbackCommand != null && !fallbackCommand.isBlank()) player.performCommand(stripSlash(fallbackCommand));
            return;
        }

        List<String> names = homes.homes(player);
        int limit = homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);

        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Home Manager")
                .content("Home tersimpan: " + names.size() + "/" + limitText + "\\nPilih menu home tanpa mengetik command.");

        addButton(builder, "Teleport Home", "home", "textures/items/ender_pearl");
        addButton(builder, "Set Home", "home-add", "textures/items/bed_red");
        addButton(builder, "Hapus Home", "delete", "textures/items/barrier");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        send(player, builder.validResultHandler(response -> sync(() -> {
            switch (response.clickedButtonId()) {
                case 0 -> showTeleportHomePicker(player, returnMenuId, fallbackCommand);
                case 1 -> showSetHomePicker(player, returnMenuId, fallbackCommand);
                case 2 -> showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                case 3 -> showConfiguredMenu(player, returnMenuId);
                default -> { }
            }
        })).build());
    }

    private void showTeleportHomePicker(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> names = homes.homes(player);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Teleport Home")
                .content(names.isEmpty() ? "Kamu belum punya home." : "Pilih home tujuan.");

        for (String name : names) addButton(builder, name, "home", "textures/items/ender_pearl");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = names.size();

        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showHomesMenu(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected < 0 || selected >= names.size()) return;
            String home = names.get(selected);
            String command = plugin.getConfig().getString("integrations.essentials-home.teleport-command", "home %home%");
            plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", home));
        })).build());
    }

    private void showSetHomePicker(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> existingHomes = homes.homes(player);
        int limit = homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);
        List<String> configured = plugin.getConfig().getStringList("integrations.essentials-home.presets");
        List<String> presets = configured.stream()
                .map(String::trim)
                .filter(name -> HOME_NAME.matcher(name).matches())
                .distinct()
                .toList();
        if (presets.isEmpty()) presets = List.of("rumah", "base", "farm", "tambang", "shop");

        boolean allowCustom = plugin.getConfig().getBoolean("integrations.essentials-home.allow-custom-name", true);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Set Home")
                .content("Home tersimpan: " + existingHomes.size() + "/" + limitText
                        + "\\nPilih nama home. Home yang sudah ada akan ditimpa setelah konfirmasi.");

        for (String preset : presets) {
            boolean existing = containsHome(existingHomes, preset);
            addButton(builder, existing ? "Timpa: " + preset : "Set: " + preset,
                    "home-add", "textures/items/bed_red");
        }
        if (allowCustom) addButton(builder, "Nama Custom", "home-add", "textures/items/name_tag");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int customIndex = allowCustom ? presets.size() : -1;
        int backIndex = presets.size() + (allowCustom ? 1 : 0);
        List<String> finalPresets = presets;
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showHomesMenu(player, returnMenuId, fallbackCommand);
                return;
            }
            if (allowCustom && selected == customIndex) {
                showNewHomeForm(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected < 0 || selected >= finalPresets.size()) return;
            confirmOrSetHome(player, finalPresets.get(selected), returnMenuId, fallbackCommand);
        })).build());
    }

    private void confirmOrSetHome(Player player, String name, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> names = homes.homes(player);
        boolean existing = containsHome(names, name);
        int limit = homes.maxHomes(player);
        if (!existing && limit >= 0 && names.size() >= limit) {
            plugin.message(player, "home-limit-reached", "%used%", Integer.toString(names.size()), "%max%", Integer.toString(limit));
            showSetHomePicker(player, returnMenuId, fallbackCommand);
            return;
        }

        if (!existing) {
            performSetHome(player, name, returnMenuId, fallbackCommand);
            return;
        }

        ModalForm form = ModalForm.builder()
                .title("Timpa Home")
                .content("Home '" + name + "' sudah ada. Timpa lokasinya dengan posisi kamu sekarang?")
                .button1("TIMPA")
                .button2("KEMBALI")
                .validResultHandler(response -> sync(() -> {
                    if (response.clickedFirst()) performSetHome(player, name, returnMenuId, fallbackCommand);
                    else showSetHomePicker(player, returnMenuId, fallbackCommand);
                }))
                .build();
        send(player, form);
    }

    private void performSetHome(Player player, String name, String returnMenuId, String fallbackCommand) {
        String command = plugin.getConfig().getString("integrations.essentials-home.set-command", "sethome %home%");
        plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", name));
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) showSetHomePicker(player, returnMenuId, fallbackCommand);
        }, 2L);
    }

    private void showNewHomeForm(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        int used = homes == null ? 0 : homes.homes(player).size();
        int limit = homes == null ? 0 : homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);

        CustomForm form = CustomForm.builder()
                .title("Nama Home Custom")
                .input("Nama Home (" + used + "/" + limitText + ")", "contoh: rumah2", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showSetHomePicker(player, returnMenuId, fallbackCommand)))
                .validResultHandler(response -> sync(() -> {
                    String rawName = response.asInput(0);
                    String name = rawName == null ? "" : rawName.trim();
                    if (!HOME_NAME.matcher(name).matches()) {
                        plugin.message(player, "invalid-home-name");
                        showNewHomeForm(player, returnMenuId, fallbackCommand);
                        return;
                    }
                    confirmOrSetHome(player, name, returnMenuId, fallbackCommand);
                }))
                .build();
        send(player, form);
    }

    private void showDeleteHomePicker(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> names = homes.homes(player);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Hapus Home")
                .content(names.isEmpty() ? "Kamu belum punya home." : "Pilih home yang ingin dihapus.");
        for (String name : names) addButton(builder, name, "delete", "textures/items/barrier");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = names.size();

        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showHomesMenu(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected < 0 || selected >= names.size()) return;
            showDeleteHomeConfirm(player, names.get(selected), returnMenuId, fallbackCommand);
        })).build());
    }

    private void showDeleteHomeConfirm(Player player, String home, String returnMenuId, String fallbackCommand) {
        ModalForm form = ModalForm.builder()
                .title("Hapus Home")
                .content("Yakin ingin menghapus home '" + home + "'?")
                .button1("HAPUS")
                .button2("KEMBALI")
                .validResultHandler(response -> sync(() -> {
                    if (response.clickedFirst()) {
                        String command = plugin.getConfig().getString("integrations.essentials-home.delete-command", "delhome %home%");
                        plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", home));
                        Bukkit.getScheduler().runTaskLater(plugin, () -> {
                            if (player.isOnline()) showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                        }, 2L);
                    } else {
                        showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                    }
                }))
                .build();
        send(player, form);
    }

    private boolean containsHome(List<String> homes, String name) {
        return homes.stream().anyMatch(home -> home.equalsIgnoreCase(name));
    }

    private void showPayPlayerSelect(Player player, String returnMenuId) {'''
s, count = pattern.subn(replacement, s, count=1)
if count != 1:
    raise SystemExit(f'home methods replacement count={count}')
p.write_text(s)

# Plugin main: version + config migration
p = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = p.read_text()
s = s.replace('CdrMemberBook v1.5.0 enabled.', 'CdrMemberBook v1.5.1 enabled.')
needle = '''        if (configVersion < 7) {
            getConfig().set("member-book.dynamic.enabled", true);
            getConfig().set("member-book.dynamic.placeholderapi", true);
            getConfig().set("member-book.dynamic.built-in-placeholders", true);
            getConfig().set("member-book.dynamic.refresh-interval-ticks", 200L);
            getConfig().set("member-book.dynamic.refresh-on-join", true);
            getConfig().set("member-book.dynamic.refresh-on-world-change", true);
        }

        getConfig().set("config-version", 7);
'''
repl = '''        if (configVersion < 7) {
            getConfig().set("member-book.dynamic.enabled", true);
            getConfig().set("member-book.dynamic.placeholderapi", true);
            getConfig().set("member-book.dynamic.built-in-placeholders", true);
            getConfig().set("member-book.dynamic.refresh-interval-ticks", 200L);
            getConfig().set("member-book.dynamic.refresh-on-join", true);
            getConfig().set("member-book.dynamic.refresh-on-world-change", true);
        }

        if (configVersion < 8) {
            getConfig().set("integrations.essentials-home.presets", java.util.List.of("rumah", "base", "farm", "tambang", "shop"));
            getConfig().set("integrations.essentials-home.allow-custom-name", true);
        }

        getConfig().set("config-version", 8);
'''
if needle not in s:
    raise SystemExit('config v7 migration pattern not found')
s = s.replace(needle, repl, 1)
p.write_text(s)

# pom.xml
p = root / 'pom.xml'
s = p.read_text().replace('<version>1.5.0</version>', '<version>1.5.1</version>', 1)
p.write_text(s)

# plugin.yml
p = root / 'src/main/resources/plugin.yml'
s = p.read_text().replace("version: '1.5.0'", "version: '1.5.1'", 1)
p.write_text(s)

# config.yml
p = root / 'src/main/resources/config.yml'
s = p.read_text()
s = s.replace('# CdrMemberBook v1.5.0', '# CdrMemberBook v1.5.1', 1)
s = s.replace('config-version: 7', 'config-version: 8', 1)
s = s.replace('# Default v1.5.0:', '# Default v1.5.1:', 1)
s = s.replace('# Legacy compatibility option. Mode default v1.5.0 tidak mengunci perpindahan internal.', '# Legacy compatibility option. Mode default v1.5.1 tidak mengunci perpindahan internal.', 1)
needle = '''    set-command: 'sethome %home%'
    teleport-command: 'home %home%'
    delete-command: 'delhome %home%'
'''
repl = '''    set-command: 'sethome %home%'
    teleport-command: 'home %home%'
    delete-command: 'delhome %home%'
    # Tombol preset untuk Bedrock Set Home. Bisa diubah bebas.
    presets:
    - rumah
    - base
    - farm
    - tambang
    - shop
    # Tetap sediakan opsi input nama sendiri selain tombol preset.
    allow-custom-name: true
'''
if needle not in s:
    raise SystemExit('config home integration pattern not found')
s = s.replace(needle, repl, 1)
p.write_text(s)

# CHANGELOG.md
p = root / 'CHANGELOG.md'
s = p.read_text()
insert_at = s.index('## 1.5.0 — Dynamic Member Book')
entry = '''## 1.5.1 — Home Picker QoL

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

'''
s = s[:insert_at] + entry + s[insert_at:]
p.write_text(s)

# README.md
p = root / 'README.md'
s = p.read_text()
s = s.replace('# CdrMemberBook v1.5.0', '# CdrMemberBook v1.5.1', 1)
s = s.replace('target/CdrMemberBook-1.5.0.jar', 'target/CdrMemberBook-1.5.1.jar')
old = '''## Bedrock Home Manager

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
'''
new = '''## Bedrock Home Manager

Gunakan `type: homes`. Mulai v1.5.1, Home Manager Bedrock memakai flow klik penuh: **Teleport Home**, **Set Home**, **Hapus Home**, lalu picker nama home. Player tidak perlu mengetik `/home` atau `/sethome`.

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
```

`Teleport Home` menampilkan home yang benar-benar dimiliki player. `Set Home` menampilkan tombol preset; preset yang sudah ada akan meminta konfirmasi sebelum ditimpa. `Nama Custom` dapat dimatikan dengan `allow-custom-name: false` jika server ingin 100% tombol tanpa input teks.

```yaml
sethome:
  enabled: true
  name: Home
  type: homes
  command: homes
  icon: textures/items/bed_red
  java-material: RED_BED
```
'''
if old not in s:
    raise SystemExit('README home section not found')
s = s.replace(old, new, 1)
p.write_text(s)
