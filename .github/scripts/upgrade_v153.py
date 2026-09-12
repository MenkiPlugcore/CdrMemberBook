from pathlib import Path
import re

root = Path('.')

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)

# -----------------------------------------------------------------------------
# BedrockFormService.java - advanced Home preset metadata/permissions
# -----------------------------------------------------------------------------
p = root / 'src/main/java/id/cadera/memberbook/form/BedrockFormService.java'
s = p.read_text()

s = replace_once(
    s,
    'import org.bukkit.Bukkit;\nimport org.bukkit.entity.Player;\n',
    'import org.bukkit.Bukkit;\nimport org.bukkit.configuration.ConfigurationSection;\nimport org.bukkit.entity.Player;\n',
    'ConfigurationSection import'
)

# Teleport picker: pretty display name/icon for configured presets, canonical name for command.
old = '''        for (String name : names) addButton(builder, name, "home", "textures/items/ender_pearl");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
'''
new = '''        for (String name : names) {
            HomePreset preset = presetForOwnedHome(name);
            String label = preset == null ? name : preset.displayName();
            String icon = preset == null ? "textures/items/ender_pearl" : preset.icon();
            addConfiguredButton(builder, plugin.formatMenuText(label, player), icon);
        }
        addButton(builder, "Kembali", "back", "textures/items/arrow");
'''
s = replace_once(s, old, new, 'teleport preset display metadata')

# Replace the whole Set Home picker with advanced presets.
pattern = re.compile(
    r'    private void showSetHomePicker\(Player player, String returnMenuId, String fallbackCommand\) \{.*?^    private void confirmOrSetHome\(Player player, String name, String returnMenuId, String fallbackCommand\) \{',
    re.S | re.M
)
replacement = '''    private void showSetHomePicker(Player player, String returnMenuId, String fallbackCommand) {
        EssentialsHomeService homes = plugin.homes();
        if (homes == null || !homes.available()) {
            showHomesMenu(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> existingHomes = sortedHomes(homes.homes(player));
        int limit = homes.maxHomes(player);
        String limitText = limit < 0 ? "∞" : Integer.toString(limit);
        List<HomePreset> presets = homePresets(player);

        boolean allowCustom = plugin.getConfig().getBoolean("integrations.essentials-home.allow-custom-name", true);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Set Home")
                .content("Home tersimpan: " + existingHomes.size() + "/" + limitText
                        + "\\nPilih preset home. Home yang sudah ada akan ditimpa setelah konfirmasi.");

        for (HomePreset preset : presets) {
            boolean existing = containsHome(existingHomes, preset.name());
            String state = preset.allowed() ? (existing ? "Timpa: " : "Set: ") : "Terkunci: ";
            addConfiguredButton(builder,
                    plugin.formatMenuText(state + preset.displayName(), player),
                    preset.icon());
        }
        if (allowCustom) addButton(builder, "Nama Custom", "home-add", "textures/items/name_tag");
        addButton(builder, "Kembali", "back", "textures/items/arrow");

        int customIndex = allowCustom ? presets.size() : -1;
        int backIndex = presets.size() + (allowCustom ? 1 : 0);
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
            if (selected < 0 || selected >= presets.size()) return;
            HomePreset preset = presets.get(selected);
            if (!preset.allowed()) {
                plugin.message(player, "home-preset-no-permission", "%home%", preset.name());
                showSetHomePicker(player, returnMenuId, fallbackCommand);
                return;
            }
            confirmOrSetHome(player, preset.name(), returnMenuId, fallbackCommand);
        })).build());
    }

    private void confirmOrSetHome(Player player, String name, String returnMenuId, String fallbackCommand) {'''
s, count = pattern.subn(lambda _: replacement, s, count=1)
if count != 1:
    raise SystemExit(f'set home picker replacement count={count}')

# Permission validation is centralized so custom-name input cannot bypass restricted preset names.
old = '''        List<String> names = homes.homes(player);
        boolean existing = containsHome(names, name);
'''
new = '''        if (!canUsePresetName(player, name)) {
            plugin.message(player, "home-preset-no-permission", "%home%", name);
            showSetHomePicker(player, returnMenuId, fallbackCommand);
            return;
        }

        List<String> names = homes.homes(player);
        boolean existing = containsHome(names, name);
'''
s = replace_once(s, old, new, 'preset permission guard')

# Delete picker: same pretty display/icon behavior as Teleport picker.
old = '''        for (String name : names) addButton(builder, name, "delete", "textures/items/barrier");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
'''
new = '''        for (String name : names) {
            HomePreset preset = presetForOwnedHome(name);
            String label = preset == null ? name : preset.displayName();
            String icon = preset == null ? "textures/items/barrier" : preset.icon();
            addConfiguredButton(builder, plugin.formatMenuText(label, player), icon);
        }
        addButton(builder, "Kembali", "back", "textures/items/arrow");
'''
s = replace_once(s, old, new, 'delete preset display metadata')

# Advanced preset helper methods are inserted before sortedHomes().
marker = '''    private List<String> sortedHomes(List<String> homes) {
'''
helpers = '''    private List<HomePreset> homePresets(Player player) {
        List<String> names = configuredPresetNames();
        boolean hideLocked = plugin.getConfig().getBoolean(
                "integrations.essentials-home.hide-locked-presets", true);

        return names.stream()
                .map(name -> presetDefinition(name, player))
                .filter(HomePreset::enabled)
                .filter(preset -> preset.allowed() || !hideLocked)
                .toList();
    }

    private List<String> configuredPresetNames() {
        List<String> configured = plugin.getConfig().getStringList("integrations.essentials-home.presets");
        List<String> names = configured.stream()
                .map(String::trim)
                .filter(name -> HOME_NAME.matcher(name).matches())
                .distinct()
                .toList();
        return names.isEmpty() ? List.of("rumah", "base", "farm", "tambang", "shop") : names;
    }

    private HomePreset presetDefinition(String name, Player player) {
        String base = "integrations.essentials-home.preset-details." + name + ".";
        boolean enabled = plugin.getConfig().getBoolean(base + "enabled", true);
        String displayName = plugin.getConfig().getString(base + "display-name", prettyHomeName(name));
        String icon = plugin.getConfig().getString(base + "icon", defaultPresetIcon(name));
        String permission = plugin.getConfig().getString(base + "permission", "");
        if (displayName == null || displayName.isBlank()) displayName = prettyHomeName(name);
        if (icon == null || icon.isBlank()) icon = defaultPresetIcon(name);
        if (permission == null) permission = "";
        boolean allowed = permission.isBlank() || player.hasPermission(permission);
        return new HomePreset(name, displayName, icon, permission, enabled, allowed);
    }

    private HomePreset presetForOwnedHome(String home) {
        if (!plugin.getConfig().getBoolean(
                "integrations.essentials-home.use-display-names-on-owned-homes", true)) return null;
        for (String preset : configuredPresetNames()) {
            if (!preset.equalsIgnoreCase(home)) continue;
            String base = "integrations.essentials-home.preset-details." + preset + ".";
            String displayName = plugin.getConfig().getString(base + "display-name", prettyHomeName(preset));
            String icon = plugin.getConfig().getString(base + "icon", defaultPresetIcon(preset));
            boolean enabled = plugin.getConfig().getBoolean(base + "enabled", true);
            return new HomePreset(preset,
                    displayName == null || displayName.isBlank() ? prettyHomeName(preset) : displayName,
                    icon == null || icon.isBlank() ? defaultPresetIcon(preset) : icon,
                    "", enabled, true);
        }
        return null;
    }

    private boolean canUsePresetName(Player player, String name) {
        for (String preset : configuredPresetNames()) {
            if (!preset.equalsIgnoreCase(name)) continue;
            String permission = plugin.getConfig().getString(
                    "integrations.essentials-home.preset-details." + preset + ".permission", "");
            return permission == null || permission.isBlank() || player.hasPermission(permission);
        }
        return true;
    }

    private String prettyHomeName(String name) {
        if (name == null || name.isBlank()) return "Home";
        return Character.toUpperCase(name.charAt(0)) + name.substring(1);
    }

    private String defaultPresetIcon(String name) {
        return switch (name.toLowerCase(Locale.ROOT)) {
            case "rumah", "home", "base" -> "textures/items/bed_red";
            case "farm", "kebun" -> "textures/items/wheat";
            case "tambang", "mine" -> "textures/items/iron_pickaxe";
            case "shop", "toko" -> "textures/items/emerald";
            default -> "textures/items/ender_pearl";
        };
    }

    private List<String> sortedHomes(List<String> homes) {
'''
s = replace_once(s, marker, helpers, 'advanced preset helpers')

# Add record before the existing PlayerChoice record.
s = replace_once(
    s,
    '    private enum TradeAction { SEND, ACCEPT, DENY }\n\n    private record PlayerChoice(UUID uuid, String name) {}\n',
    '    private enum TradeAction { SEND, ACCEPT, DENY }\n\n'
    '    private record HomePreset(String name, String displayName, String icon, String permission,\n'
    '                              boolean enabled, boolean allowed) {}\n\n'
    '    private record PlayerChoice(UUID uuid, String name) {}\n',
    'HomePreset record'
)
p.write_text(s)

# -----------------------------------------------------------------------------
# Main plugin - version + config v10 migration
# -----------------------------------------------------------------------------
p = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = p.read_text()
s = replace_once(s, 'CdrMemberBook v1.5.2 enabled.', 'CdrMemberBook v1.5.3 enabled.', 'enable log version')
old = '''        if (configVersion < 9) {
            getConfig().set("member-book.open-cooldown-ticks", 20L);
            getConfig().set("integrations.essentials-home.sort-alphabetically", true);
            getConfig().set("integrations.essentials-home.show-refresh-button", true);
        }

        getConfig().set("config-version", 9);
'''
new = '''        if (configVersion < 9) {
            getConfig().set("member-book.open-cooldown-ticks", 20L);
            getConfig().set("integrations.essentials-home.sort-alphabetically", true);
            getConfig().set("integrations.essentials-home.show-refresh-button", true);
        }

        if (configVersion < 10) {
            getConfig().set("integrations.essentials-home.hide-locked-presets", true);
            getConfig().set("integrations.essentials-home.use-display-names-on-owned-homes", true);
            setPresetDefaults("rumah", "Rumah", "textures/items/bed_red");
            setPresetDefaults("base", "Base", "textures/items/bed_red");
            setPresetDefaults("farm", "Farm", "textures/items/wheat");
            setPresetDefaults("tambang", "Tambang", "textures/items/iron_pickaxe");
            setPresetDefaults("shop", "Shop", "textures/items/emerald");
        }

        getConfig().set("config-version", 10);
'''
s = replace_once(s, old, new, 'config v10 migration')

marker = '''    private void migrateSpecialButton(String key, String expectedCommand, String newType, String fallbackCommand) {
'''
helper = '''    private void setPresetDefaults(String name, String displayName, String icon) {
        String base = "integrations.essentials-home.preset-details." + name + ".";
        if (!getConfig().isSet(base + "enabled")) getConfig().set(base + "enabled", true);
        if (!getConfig().isSet(base + "display-name")) getConfig().set(base + "display-name", displayName);
        if (!getConfig().isSet(base + "icon")) getConfig().set(base + "icon", icon);
        if (!getConfig().isSet(base + "permission")) getConfig().set(base + "permission", "");
    }

    private void migrateSpecialButton(String key, String expectedCommand, String newType, String fallbackCommand) {
'''
s = replace_once(s, marker, helper, 'setPresetDefaults helper')
p.write_text(s)

# -----------------------------------------------------------------------------
# Versions
# -----------------------------------------------------------------------------
p = root / 'pom.xml'
s = p.read_text()
s = replace_once(s, '<version>1.5.2</version>', '<version>1.5.3</version>', 'pom version')
p.write_text(s)

p = root / 'src/main/resources/plugin.yml'
s = p.read_text()
s = replace_once(s, "version: '1.5.2'", "version: '1.5.3'", 'plugin yml version')
p.write_text(s)

# -----------------------------------------------------------------------------
# config.yml
# -----------------------------------------------------------------------------
p = root / 'src/main/resources/config.yml'
s = p.read_text()
s = replace_once(s, '# CdrMemberBook v1.5.2', '# CdrMemberBook v1.5.3', 'config header')
s = replace_once(s, 'config-version: 9', 'config-version: 10', 'config version')
s = s.replace('# Default v1.5.2:', '# Default v1.5.3:', 1)
s = s.replace('# Legacy compatibility option. Mode default v1.5.2 tidak mengunci perpindahan internal.',
              '# Legacy compatibility option. Mode default v1.5.3 tidak mengunci perpindahan internal.', 1)
old = '''    # Tambahkan tombol Refresh Home di Home Manager.
    show-refresh-button: true
'''
new = '''    # Tambahkan tombol Refresh Home di Home Manager.
    show-refresh-button: true
    # Preset yang player tidak punya permission disembunyikan dari Set Home.
    # false = preset tetap tampil dengan label Terkunci.
    hide-locked-presets: true
    # Pakai display-name + icon preset juga pada Teleport/Hapus home yang sudah dimiliki.
    use-display-names-on-owned-homes: true

    # Metadata advanced per preset. Key harus sama dengan nama di list `presets`.
    # `permission` kosong = semua player boleh Set/Timpa preset tersebut.
    # Permission hanya membatasi Set/Timpa. Home yang sudah dimiliki tetap bisa diteleport/hapus.
    preset-details:
      rumah:
        enabled: true
        display-name: 'Rumah'
        icon: textures/items/bed_red
        permission: ''
      base:
        enabled: true
        display-name: 'Base'
        icon: textures/items/bed_red
        permission: ''
      farm:
        enabled: true
        display-name: 'Farm'
        icon: textures/items/wheat
        permission: ''
      tambang:
        enabled: true
        display-name: 'Tambang'
        icon: textures/items/iron_pickaxe
        permission: ''
      shop:
        enabled: true
        display-name: 'Shop'
        icon: textures/items/emerald
        permission: ''
'''
s = replace_once(s, old, new, 'advanced preset config')
s = replace_once(
    s,
    "  home-delete-success: '&aHome &f%home% &aberhasil dihapus.'\n",
    "  home-delete-success: '&aHome &f%home% &aberhasil dihapus.'\n"
    "  home-preset-no-permission: '&cKamu tidak punya izin untuk menggunakan preset home &f%home%&c.'\n",
    'preset permission message'
)
p.write_text(s)

# -----------------------------------------------------------------------------
# CHANGELOG
# -----------------------------------------------------------------------------
p = root / 'CHANGELOG.md'
s = p.read_text()
marker = '## 1.5.2 — Bedrock Menu QoL\n'
entry = '''## 1.5.3 — Home Manager Advanced

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

'''
if marker not in s:
    raise SystemExit('changelog marker missing')
s = s.replace(marker, entry + marker, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# README
# -----------------------------------------------------------------------------
p = root / 'README.md'
s = p.read_text()
s = replace_once(s, '# CdrMemberBook v1.5.2', '# CdrMemberBook v1.5.3', 'readme title')
old = '''`v1.5.2` juga menambahkan anti-double-open Member Book default 20 ticks (1 detik), state `BELUM ADA` untuk player tanpa home, serta feedback sukses setelah set/overwrite dan delete home.
'''
new = '''`v1.5.2` menambahkan anti-double-open Member Book default 20 ticks (1 detik), state `BELUM ADA` untuk player tanpa home, serta feedback sukses setelah set/overwrite dan delete home.

`v1.5.3` menambahkan metadata advanced per preset: display name, icon Bedrock, enable/disable, dan permission. Permission preset hanya membatasi Set/Timpa; home yang sudah dimiliki tetap dapat diteleport atau dihapus.
'''
s = replace_once(s, old, new, 'readme v153 intro')
old = '''    allow-custom-name: true
```

`Teleport Home` menampilkan home yang benar-benar dimiliki player. `Set Home` menampilkan tombol preset; preset yang sudah ada akan meminta konfirmasi sebelum ditimpa. `Nama Custom` dapat dimatikan dengan `allow-custom-name: false` jika server ingin 100% tombol tanpa input teks.
'''
new = '''    allow-custom-name: true
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
'''
s = replace_once(s, old, new, 'readme advanced preset sample')
s = s.replace('target/CdrMemberBook-1.5.2.jar', 'target/CdrMemberBook-1.5.3.jar')
p.write_text(s)

print('v1.5.3 patch applied')
