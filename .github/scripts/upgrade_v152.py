from pathlib import Path

root = Path('.')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)

# -----------------------------------------------------------------------------
# MemberBookService.java - anti double-open cooldown for Member Book interaction
# -----------------------------------------------------------------------------
p = root / 'src/main/java/id/cadera/memberbook/item/MemberBookService.java'
s = p.read_text()

s = replace_once(
    s,
    '    private final Set<UUID> recoverySuppressed = new HashSet<>();\n',
    '    private final Set<UUID> recoverySuppressed = new HashSet<>();\n'
    '    private final Set<UUID> menuOpenCooldown = new HashSet<>();\n',
    'member book cooldown field'
)

old = '''    @EventHandler
    public void onInteract(PlayerInteractEvent event) {
        if (!isEligibleForBook(event.getPlayer())) return;
        Action action = event.getAction();
        if (action != Action.RIGHT_CLICK_AIR && action != Action.RIGHT_CLICK_BLOCK) return;
        if (!isMemberBook(event.getItem())) return;

        event.setCancelled(true);
        plugin.openMenu(event.getPlayer());
    }
'''
new = '''    @EventHandler
    public void onInteract(PlayerInteractEvent event) {
        Player player = event.getPlayer();
        if (!isEligibleForBook(player)) return;
        Action action = event.getAction();
        if (action != Action.RIGHT_CLICK_AIR && action != Action.RIGHT_CLICK_BLOCK) return;
        if (!isMemberBook(event.getItem())) return;

        event.setCancelled(true);
        UUID uuid = player.getUniqueId();
        long cooldownTicks = Math.max(0L, plugin.getConfig().getLong("member-book.open-cooldown-ticks", 20L));
        if (cooldownTicks > 0L) {
            if (!menuOpenCooldown.add(uuid)) return;
            Bukkit.getScheduler().runTaskLater(plugin, () -> menuOpenCooldown.remove(uuid), cooldownTicks);
        }
        plugin.openMenu(player);
    }
'''
s = replace_once(s, old, new, 'onInteract cooldown')

old = '''    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        Player player = event.getPlayer();
        if (!isMemberBook(player.getItemOnCursor())) return;
'''
new = '''    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        Player player = event.getPlayer();
        menuOpenCooldown.remove(player.getUniqueId());
        if (!isMemberBook(player.getItemOnCursor())) return;
'''
s = replace_once(s, old, new, 'quit cooldown cleanup')
p.write_text(s)

# -----------------------------------------------------------------------------
# BedrockFormService.java - Home Manager QoL
# -----------------------------------------------------------------------------
p = root / 'src/main/java/id/cadera/memberbook/form/BedrockFormService.java'
s = p.read_text()

old = '''        List<String> names = homes.homes(player);
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
'''
new = '''        List<String> names = sortedHomes(homes.homes(player));
        int limit = homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);
        boolean showRefresh = plugin.getConfig().getBoolean(
                "integrations.essentials-home.show-refresh-button", true);

        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Home Manager")
                .content("Home tersimpan: " + names.size() + "/" + limitText
                        + "\\nPilih menu home tanpa mengetik command.");

        addButton(builder, names.isEmpty() ? "Teleport Home (BELUM ADA)" : "Teleport Home (" + names.size() + ")",
                "home", "textures/items/ender_pearl");
        addButton(builder, "Set Home", "home-add", "textures/items/bed_red");
        addButton(builder, names.isEmpty() ? "Hapus Home (BELUM ADA)" : "Hapus Home (" + names.size() + ")",
                "delete", "textures/items/barrier");
        if (showRefresh) addButton(builder, "Refresh Home", "refresh", "textures/items/compass_item");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int refreshIndex = showRefresh ? 3 : -1;
        int backIndex = showRefresh ? 4 : 3;
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == 0) {
                showTeleportHomePicker(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected == 1) {
                showSetHomePicker(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected == 2) {
                showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected == refreshIndex) {
                plugin.message(player, "home-list-refreshed");
                showHomesMenu(player, returnMenuId, fallbackCommand);
                return;
            }
            if (selected == backIndex) showConfiguredMenu(player, returnMenuId);
        })).build());
'''
s = replace_once(s, old, new, 'home manager refresh')

s = replace_once(
    s,
    '        List<String> names = homes.homes(player);\n        SimpleForm.Builder builder = SimpleForm.builder()\n                .title("Teleport Home")',
    '        List<String> names = sortedHomes(homes.homes(player));\n        SimpleForm.Builder builder = SimpleForm.builder()\n                .title("Teleport Home")',
    'teleport home sort'
)

s = replace_once(
    s,
    '        List<String> existingHomes = homes.homes(player);\n        int limit = homes.maxHomes(player);',
    '        List<String> existingHomes = sortedHomes(homes.homes(player));\n        int limit = homes.maxHomes(player);',
    'set home existing sort'
)

old = '''    private void performSetHome(Player player, String name, String returnMenuId, String fallbackCommand) {
        String command = plugin.getConfig().getString("integrations.essentials-home.set-command", "sethome %home%");
        plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", name));
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) showSetHomePicker(player, returnMenuId, fallbackCommand);
        }, 2L);
    }
'''
new = '''    private void performSetHome(Player player, String name, String returnMenuId, String fallbackCommand) {
        String command = plugin.getConfig().getString("integrations.essentials-home.set-command", "sethome %home%");
        plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", name));
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline()) return;
            plugin.message(player, "home-set-success", "%home%", name);
            showSetHomePicker(player, returnMenuId, fallbackCommand);
        }, 2L);
    }
'''
s = replace_once(s, old, new, 'set home success feedback')

s = replace_once(
    s,
    '        List<String> names = homes.homes(player);\n        SimpleForm.Builder builder = SimpleForm.builder()\n                .title("Hapus Home")',
    '        List<String> names = sortedHomes(homes.homes(player));\n        SimpleForm.Builder builder = SimpleForm.builder()\n                .title("Hapus Home")',
    'delete home sort'
)

old = '''                        plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", home));
                        Bukkit.getScheduler().runTaskLater(plugin, () -> {
                            if (player.isOnline()) showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                        }, 2L);
'''
new = '''                        plugin.dispatchPlayerTemplate(player, command, Map.of("%home%", home));
                        Bukkit.getScheduler().runTaskLater(plugin, () -> {
                            if (!player.isOnline()) return;
                            plugin.message(player, "home-delete-success", "%home%", home);
                            showDeleteHomePicker(player, returnMenuId, fallbackCommand);
                        }, 2L);
'''
s = replace_once(s, old, new, 'delete home success feedback')

old = '''    private boolean containsHome(List<String> homes, String name) {
        return homes.stream().anyMatch(home -> home.equalsIgnoreCase(name));
    }

    private void showPayPlayerSelect(Player player, String returnMenuId) {
'''
new = '''    private List<String> sortedHomes(List<String> homes) {
        if (!plugin.getConfig().getBoolean("integrations.essentials-home.sort-alphabetically", true)) {
            return List.copyOf(homes);
        }
        return homes.stream().sorted(String.CASE_INSENSITIVE_ORDER).toList();
    }

    private boolean containsHome(List<String> homes, String name) {
        return homes.stream().anyMatch(home -> home.equalsIgnoreCase(name));
    }

    private void showPayPlayerSelect(Player player, String returnMenuId) {
'''
s = replace_once(s, old, new, 'sortedHomes helper')
p.write_text(s)

# -----------------------------------------------------------------------------
# Main plugin: version + config v9 migration
# -----------------------------------------------------------------------------
p = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = p.read_text()
s = replace_once(s, 'CdrMemberBook v1.5.1 enabled.', 'CdrMemberBook v1.5.2 enabled.', 'enable log version')
old = '''        if (configVersion < 8) {
            getConfig().set("integrations.essentials-home.presets", java.util.List.of("rumah", "base", "farm", "tambang", "shop"));
            getConfig().set("integrations.essentials-home.allow-custom-name", true);
        }

        getConfig().set("config-version", 8);
'''
new = '''        if (configVersion < 8) {
            getConfig().set("integrations.essentials-home.presets", java.util.List.of("rumah", "base", "farm", "tambang", "shop"));
            getConfig().set("integrations.essentials-home.allow-custom-name", true);
        }

        if (configVersion < 9) {
            getConfig().set("member-book.open-cooldown-ticks", 20L);
            getConfig().set("integrations.essentials-home.sort-alphabetically", true);
            getConfig().set("integrations.essentials-home.show-refresh-button", true);
        }

        getConfig().set("config-version", 9);
'''
s = replace_once(s, old, new, 'config v9 migration')
p.write_text(s)

# -----------------------------------------------------------------------------
# Version files
# -----------------------------------------------------------------------------
p = root / 'pom.xml'
s = p.read_text()
s = replace_once(s, '<version>1.5.1</version>', '<version>1.5.2</version>', 'pom version')
p.write_text(s)

p = root / 'src/main/resources/plugin.yml'
s = p.read_text()
s = replace_once(s, "version: '1.5.1'", "version: '1.5.2'", 'plugin yml version')
p.write_text(s)

# -----------------------------------------------------------------------------
# config.yml
# -----------------------------------------------------------------------------
p = root / 'src/main/resources/config.yml'
s = p.read_text()
s = replace_once(s, '# CdrMemberBook v1.5.1', '# CdrMemberBook v1.5.2', 'config header')
s = replace_once(s, 'config-version: 8', 'config-version: 9', 'config version')
s = s.replace('# Default v1.5.1:', '# Default v1.5.2:', 1)
s = s.replace('# Legacy compatibility option. Mode default v1.5.1 tidak mengunci perpindahan internal.',
              '# Legacy compatibility option. Mode default v1.5.2 tidak mengunci perpindahan internal.', 1)
s = replace_once(
    s,
    '  prevent-drop: true\n\n  # Safety & Recovery v1.4.0',
    '  prevent-drop: true\n  # Anti double-open form. 20 ticks = 1 detik; 0 = nonaktif.\n  open-cooldown-ticks: 20\n\n  # Safety & Recovery v1.4.0',
    'open cooldown config'
)
s = replace_once(
    s,
    '    # Tetap sediakan opsi input nama sendiri selain tombol preset.\n    allow-custom-name: true\n',
    '    # Tetap sediakan opsi input nama sendiri selain tombol preset.\n    allow-custom-name: true\n'
    '    # Urutkan daftar home aktual milik player secara alfabetis.\n    sort-alphabetically: true\n'
    '    # Tambahkan tombol Refresh Home di Home Manager.\n    show-refresh-button: true\n',
    'home qos config'
)
s = replace_once(
    s,
    '  invalid-home-name: \'&cNama home hanya boleh huruf, angka, _ atau - (maks 32 karakter).\'\n',
    '  invalid-home-name: \'&cNama home hanya boleh huruf, angka, _ atau - (maks 32 karakter).\'\n'
    '  home-list-refreshed: \'&aDaftar home diperbarui.\'\n'
    '  home-set-success: \'&aHome &f%home% &aberhasil disimpan/diperbarui.\'\n'
    '  home-delete-success: \'&aHome &f%home% &aberhasil dihapus.\'\n',
    'home qol messages'
)
# Icon key is optional because addButton has fallback; expose it for config consistency.
s = replace_once(
    s,
    '  delete: textures/items/barrier\n  trade-send:',
    '  delete: textures/items/barrier\n  refresh: textures/items/compass_item\n  trade-send:',
    'refresh icon'
)
p.write_text(s)

# -----------------------------------------------------------------------------
# README + changelog
# -----------------------------------------------------------------------------
p = root / 'CHANGELOG.md'
s = p.read_text()
marker = '## 1.5.1 — Home Picker QoL\n'
entry = '''## 1.5.2 — Bedrock Menu QoL

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

'''
if marker not in s:
    raise SystemExit('changelog marker missing')
s = s.replace(marker, entry + marker, 1)
p.write_text(s)

p = root / 'README.md'
s = p.read_text()
s = replace_once(s, '# CdrMemberBook v1.5.1', '# CdrMemberBook v1.5.2', 'readme title')
old = '''## Bedrock Home Manager

Gunakan `type: homes`. CdrMemberBook membaca data home dan limit langsung dari EssentialsX, lalu menyediakan daftar home, set home baru, teleport, hapus dengan konfirmasi, serta dukungan home unlimited.
'''
new = '''## Bedrock Home Manager

Gunakan `type: homes`. CdrMemberBook membaca data home dan limit langsung dari EssentialsX. Flow Bedrock bersifat click-first: `Teleport Home`, `Set Home`, `Hapus Home`, dan `Refresh Home`. Daftar home aktual otomatis muncul sebagai tombol, diurutkan alfabetis secara default, dan tidak mengharuskan player mengetik `/home`.

`v1.5.2` juga menambahkan anti-double-open Member Book default 20 ticks (1 detik), state `BELUM ADA` untuk player tanpa home, serta feedback sukses setelah set/overwrite dan delete home.
'''
s = replace_once(s, old, new, 'readme home manager text')
s = s.replace('target/CdrMemberBook-1.5.1.jar', 'target/CdrMemberBook-1.5.2.jar')
p.write_text(s)

print('v1.5.2 patch applied')
