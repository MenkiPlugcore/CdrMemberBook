from pathlib import Path
import re

root = Path('.')

# MemberBookService.java
p = root / 'src/main/java/id/cadera/memberbook/item/MemberBookService.java'
s = p.read_text()
if 'import me.clip.placeholderapi.PlaceholderAPI;' not in s:
    s = s.replace('import id.cadera.memberbook.util.Colors;\n', 'import id.cadera.memberbook.util.Colors;\nimport me.clip.placeholderapi.PlaceholderAPI;\n')

s = s.replace('    private BukkitTask enforcementTask;\n', '    private BukkitTask enforcementTask;\n    private BukkitTask dynamicRefreshTask;\n')

old = '''    public void startEnforcement() {
        stopEnforcement();
        if (!isEnabled()) return;
        if (!isPermanentHotbar() && !recoveryEnabled()) return;

        long configuredPeriod = isPermanentHotbar()
                ? plugin.getConfig().getLong("member-book.enforce-interval-ticks", 20L)
                : plugin.getConfig().getLong("member-book.recovery.interval-ticks", 100L);
        long period = Math.max(20L, configuredPeriod);

        enforcementTask = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
            for (Player player : Bukkit.getOnlinePlayers()) {
                syncBookState(player, false);
            }
        }, period, period);
    }
'''
new = '''    public void startEnforcement() {
        stopEnforcement();
        if (!isEnabled()) return;

        if (isPermanentHotbar() || recoveryEnabled()) {
            long configuredPeriod = isPermanentHotbar()
                    ? plugin.getConfig().getLong("member-book.enforce-interval-ticks", 20L)
                    : plugin.getConfig().getLong("member-book.recovery.interval-ticks", 100L);
            long period = Math.max(20L, configuredPeriod);

            enforcementTask = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
                for (Player player : Bukkit.getOnlinePlayers()) {
                    syncBookState(player, false);
                }
            }, period, period);
        }

        startDynamicRefresh();
    }

    private void startDynamicRefresh() {
        if (!dynamicEnabled()) return;
        long period = Math.max(40L, plugin.getConfig().getLong(
                "member-book.dynamic.refresh-interval-ticks", 200L));
        dynamicRefreshTask = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
            for (Player player : Bukkit.getOnlinePlayers()) {
                refreshDynamicBook(player);
            }
        }, period, period);
    }
'''
if old not in s:
    raise SystemExit('startEnforcement pattern not found')
s = s.replace(old, new, 1)

old = '''    public void stopEnforcement() {
        if (enforcementTask != null) {
            enforcementTask.cancel();
            enforcementTask = null;
        }
    }
'''
new = '''    public void stopEnforcement() {
        if (enforcementTask != null) {
            enforcementTask.cancel();
            enforcementTask = null;
        }
        if (dynamicRefreshTask != null) {
            dynamicRefreshTask.cancel();
            dynamicRefreshTask = null;
        }
    }
'''
s = s.replace(old, new, 1)

# make refresh method public and add targeted refresh helper
s = s.replace('    private void refreshVisibleBookAppearance(Player player) {', '    public void refreshVisibleBookAppearance(Player player) {', 1)
marker = '''    private ItemStack refreshedBook() {
        ItemStack refreshed = createBook();
        refreshed.setAmount(1);
        return refreshed;
    }
'''
replacement = '''    private ItemStack refreshedBook(Player player) {
        ItemStack refreshed = createBook(player);
        refreshed.setAmount(1);
        return refreshed;
    }

    public boolean refreshDynamicBook(Player player) {
        if (!dynamicEnabled() || !isEligibleForBook(player)
                || recoverySuppressed.contains(player.getUniqueId()) || !hasOwnedBook(player)) {
            return false;
        }
        refreshVisibleBookAppearance(player);
        return true;
    }
'''
if marker not in s:
    raise SystemExit('refreshedBook marker not found')
s = s.replace(marker, replacement, 1)

# convert createBook to player-aware
s = s.replace('placeBookInPlayer(player, createBook())', 'placeBookInPlayer(player, createBook(player))')
s = s.replace('ItemStack book = sourceSlot >= 0 ? inventory.getItem(sourceSlot) : createBook();', 'ItemStack book = sourceSlot >= 0 ? inventory.getItem(sourceSlot) : createBook(player);')
s = s.replace('if (book == null) book = createBook();', 'if (book == null) book = createBook(player);')
s = s.replace('    private ItemStack createBook() {', '    private ItemStack createBook(Player player) {', 1)
s = s.replace('        applyConfiguredAppearance(item);', '        applyConfiguredAppearance(item, player);', 1)
s = s.replace('    private void applyConfiguredAppearance(ItemStack item) {', '    private void applyConfiguredAppearance(ItemStack item, Player player) {', 1)

# dynamic text for name/lore
old = '''        meta.setDisplayName(Colors.legacy(plugin.getConfig().getString(
                "member-book.name", "&d&lMOONSIGN &fMember Book")));

        List<String> lore = new ArrayList<>();
        for (String line : plugin.getConfig().getStringList("member-book.lore")) {
            lore.add(Colors.legacy(line));
        }
'''
new = '''        String configuredName = plugin.getConfig().getString(
                "member-book.name", "&d&lMOONSIGN &fMember Book");
        meta.setDisplayName(Colors.legacy(renderDynamicText(player, configuredName)));

        List<String> lore = new ArrayList<>();
        for (String line : plugin.getConfig().getStringList("member-book.lore")) {
            lore.add(Colors.legacy(renderDynamicText(player, line)));
        }
'''
if old not in s:
    raise SystemExit('name/lore pattern not found')
s = s.replace(old, new, 1)

# calls to refreshedBook now need player
s = s.replace('inventory.setItem(slot, refreshedBook());', 'inventory.setItem(slot, refreshedBook(player));')
s = s.replace('player.setItemOnCursor(refreshedBook());', 'player.setItemOnCursor(refreshedBook(player));')
s = s.replace('top.setItem(slot, refreshedBook());', 'top.setItem(slot, refreshedBook(player));')

# add render helpers before refreshExistingEnabled
anchor = '''    private boolean refreshExistingEnabled() {
        return plugin.getConfig().getBoolean("member-book.customization.refresh-existing", true);
    }
'''
block = '''    private String renderDynamicText(Player player, String value) {
        if (value == null || value.isEmpty()) return "";
        String rendered = value;

        if (plugin.getConfig().getBoolean("member-book.dynamic.built-in-placeholders", true)) {
            rendered = rendered
                    .replace("%player%", player.getName())
                    .replace("%uuid%", player.getUniqueId().toString())
                    .replace("%world%", player.getWorld().getName())
                    .replace("%ping%", Integer.toString(player.getPing()))
                    .replace("%online%", Integer.toString(Bukkit.getOnlinePlayers().size()));
        }

        if (placeholderApiEnabled()
                && plugin.getConfig().getBoolean("member-book.dynamic.placeholderapi", true)) {
            try {
                rendered = PlaceholderAPI.setPlaceholders(player, rendered);
            } catch (Throwable ignored) {
                // Keep built-in/original text if PlaceholderAPI or an expansion fails.
            }
        }
        return rendered;
    }

    private boolean placeholderApiEnabled() {
        return Bukkit.getPluginManager().isPluginEnabled("PlaceholderAPI");
    }

    private boolean dynamicEnabled() {
        return plugin.getConfig().getBoolean("member-book.dynamic.enabled", true);
    }

    private boolean refreshExistingEnabled() {
        return plugin.getConfig().getBoolean("member-book.customization.refresh-existing", true);
    }
'''
if anchor not in s:
    raise SystemExit('refreshExisting anchor not found')
s = s.replace(anchor, block, 1)

# join and world-change dynamic refresh
old = '''        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline()) return;
            if (isEligibleForBook(player) && refreshExistingEnabled()) refreshVisibleBookAppearance(player);
            syncBookState(player, true);
        }, delay);
'''
new = '''        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline()) return;
            if (isEligibleForBook(player) && (refreshExistingEnabled()
                    || plugin.getConfig().getBoolean("member-book.dynamic.refresh-on-join", true))) {
                refreshVisibleBookAppearance(player);
            }
            syncBookState(player, true);
        }, delay);
'''
if old in s:
    s = s.replace(old, new, 1)

old = '''        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) syncBookState(player, false);
        }, 1L);
'''
new = '''        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline()) return;
            if (dynamicEnabled() && plugin.getConfig().getBoolean(
                    "member-book.dynamic.refresh-on-world-change", true)) {
                refreshDynamicBook(player);
            }
            syncBookState(player, false);
        }, 1L);
'''
# replace last matching block (world change), not respawn
idx = s.find(old, s.find('public void onWorldChange'))
if idx != -1:
    s = s[:idx] + new + s[idx+len(old):]

# sanity: no zero-arg create/refreshedBook remain
if 'createBook()' in s or 'refreshedBook()' in s:
    raise SystemExit('zero-arg createBook/refreshedBook remains')
p.write_text(s)

# Plugin main version/config migration/log
p = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = p.read_text()
s = s.replace('CdrMemberBook v1.4.1 enabled.', 'CdrMemberBook v1.5.0 enabled.')
needle = '''        if (configVersion < 6) {
            getConfig().set("member-book.customization.custom-model-data", 0);
            getConfig().set("member-book.customization.item-model", "");
            getConfig().set("member-book.customization.enchant-glint", "default");
            getConfig().set("member-book.customization.hide-tooltip", false);
            getConfig().set("member-book.customization.hide-attributes", false);
            getConfig().set("member-book.customization.hide-additional-tooltip", false);
            getConfig().set("member-book.customization.item-flags", java.util.List.of());
            getConfig().set("member-book.customization.refresh-existing", true);
        }

        getConfig().set("config-version", 6);
'''
repl = '''        if (configVersion < 6) {
            getConfig().set("member-book.customization.custom-model-data", 0);
            getConfig().set("member-book.customization.item-model", "");
            getConfig().set("member-book.customization.enchant-glint", "default");
            getConfig().set("member-book.customization.hide-tooltip", false);
            getConfig().set("member-book.customization.hide-attributes", false);
            getConfig().set("member-book.customization.hide-additional-tooltip", false);
            getConfig().set("member-book.customization.item-flags", java.util.List.of());
            getConfig().set("member-book.customization.refresh-existing", true);
        }

        if (configVersion < 7) {
            getConfig().set("member-book.dynamic.enabled", true);
            getConfig().set("member-book.dynamic.placeholderapi", true);
            getConfig().set("member-book.dynamic.built-in-placeholders", true);
            getConfig().set("member-book.dynamic.refresh-interval-ticks", 200L);
            getConfig().set("member-book.dynamic.refresh-on-join", true);
            getConfig().set("member-book.dynamic.refresh-on-world-change", true);
        }

        getConfig().set("config-version", 7);
'''
if needle not in s:
    raise SystemExit('config v6 migration pattern not found')
s = s.replace(needle, repl, 1)

insert = '''        } else {
            getLogger().info("Floodgate not detected: Java inventory fallback only.");
        }

        registerCommands();
'''
insert_repl = '''        } else {
            getLogger().info("Floodgate not detected: Java inventory fallback only.");
        }

        if (Bukkit.getPluginManager().isPluginEnabled("PlaceholderAPI")) {
            getLogger().info("PlaceholderAPI detected: Dynamic Member Book placeholders enabled.");
        } else {
            getLogger().info("PlaceholderAPI not detected: Dynamic Member Book will use built-in placeholders only.");
        }

        registerCommands();
'''
if insert not in s:
    raise SystemExit('PAPI log insert point not found')
s = s.replace(insert, insert_repl, 1)
p.write_text(s)

# Admin command: refresh
p = root / 'src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'
s = p.read_text()
needle = '''            case "fix" -> {
                if (!service.isEligibleForBook(target)) {
                    sender.sendMessage(Colors.legacy("&e" + target.getName()
                            + " &cbukan player yang eligible menerima Member Book (default: Bedrock/Floodgate only)."));
                    return true;
                }
                boolean success = service.forceRepair(target);
                if (success) {
                    sender.sendMessage(Colors.legacy("&aMember Book &f" + target.getName()
                            + " &aberhasil diperiksa: duplicate dibersihkan dan recovery dijalankan."));
                } else {
                    sender.sendMessage(Colors.legacy("&eRecovery belum bisa menaruh buku ke inventory/cursor &f"
                            + target.getName() + "&e karena penuh."));
                }
            }
'''
repl = needle + '''            case "refresh" -> {
                if (!service.isEligibleForBook(target)) {
                    sender.sendMessage(Colors.legacy("&e" + target.getName()
                            + " &cbukan player yang eligible menerima Member Book (default: Bedrock/Floodgate only)."));
                    return true;
                }
                boolean success = service.refreshDynamicBook(target);
                if (success) {
                    sender.sendMessage(Colors.legacy("&aDynamic Member Book &f" + target.getName()
                            + " &aberhasil direfresh."));
                } else {
                    sender.sendMessage(Colors.legacy("&eTidak ada Member Book aktif yang bisa direfresh untuk &f"
                            + target.getName() + "&e."));
                }
            }
'''
if needle not in s:
    raise SystemExit('admin fix case not found')
s = s.replace(needle, repl, 1)
s = s.replace('&dCdrMemberBook &fv1.4.0', '&dCdrMemberBook &fv1.5.0')
s = s.replace('sender.sendMessage(Colors.legacy("&f/" + label + " fix <player> &8- &7bersihkan duplicate + recovery"));', 'sender.sendMessage(Colors.legacy("&f/" + label + " fix <player> &8- &7bersihkan duplicate + recovery"));\n        sender.sendMessage(Colors.legacy("&f/" + label + " refresh <player> &8- &7refresh placeholder nama/lore"));')
s = s.replace('List.of("give", "remove", "fix")', 'List.of("give", "remove", "fix", "refresh")')
p.write_text(s)

# pom
p = root / 'pom.xml'
s = p.read_text().replace('<version>1.4.1</version>', '<version>1.5.0</version>', 1)
repo_marker = '''        <repository>
            <id>essentialsx-releases</id>
            <url>https://repo.essentialsx.net/releases/</url>
        </repository>
'''
repo_add = repo_marker + '''        <repository>
            <id>placeholderapi</id>
            <url>https://repo.helpch.at/releases</url>
        </repository>
'''
if '<id>placeholderapi</id>' not in s:
    s = s.replace(repo_marker, repo_add, 1)
dep_marker = '''        <dependency>
            <groupId>net.essentialsx</groupId>
            <artifactId>EssentialsX</artifactId>
            <version>2.21.2</version>
            <scope>provided</scope>
        </dependency>
'''
dep_add = dep_marker + '''        <dependency>
            <groupId>me.clip</groupId>
            <artifactId>placeholderapi</artifactId>
            <version>2.12.3</version>
            <scope>provided</scope>
        </dependency>
'''
if '<artifactId>placeholderapi</artifactId>' not in s:
    s = s.replace(dep_marker, dep_add, 1)
p.write_text(s)

# plugin.yml
p = root / 'src/main/resources/plugin.yml'
s = p.read_text().replace("version: '1.4.1'", "version: '1.5.0'", 1)
if '  - PlaceholderAPI\n' not in s:
    s = s.replace('  - AxTrade\n', '  - AxTrade\n  - PlaceholderAPI\n', 1)
s = s.replace('usage: /cdrmemberbook <give|remove|fix> <player>', 'usage: /cdrmemberbook <give|remove|fix|refresh> <player>')
p.write_text(s)

# config.yml
p = root / 'src/main/resources/config.yml'
s = p.read_text()
s = s.replace('# CdrMemberBook v1.4.1', '# CdrMemberBook v1.5.0', 1)
s = s.replace('config-version: 6', 'config-version: 7', 1)
s = s.replace('# Default v1.4.1:', '# Default v1.5.0:', 1)
s = s.replace('# Legacy compatibility option. Mode default v1.4.1 tidak mengunci perpindahan internal.', '# Legacy compatibility option. Mode default v1.5.0 tidak mengunci perpindahan internal.', 1)
anchor = '''    # Buku lama milik player online otomatis mengikuti tampilan config terbaru saat reload/join.
    refresh-existing: true
'''
block = anchor + '''
  # Dynamic Member Book v1.5.0
  dynamic:
    enabled: true
    # PlaceholderAPI bersifat optional. Jika tidak terpasang, placeholder bawaan tetap bekerja.
    placeholderapi: true
    built-in-placeholders: true
    # 200 ticks = 10 detik. Minimum internal 40 ticks agar tetap ringan.
    refresh-interval-ticks: 200
    refresh-on-join: true
    refresh-on-world-change: true
    # Built-in placeholders: %player%, %uuid%, %world%, %ping%, %online%
    # PlaceholderAPI examples: %luckperms_prefix%, %vault_eco_balance_formatted%, dll.
'''
if anchor not in s:
    raise SystemExit('config customization anchor not found')
s = s.replace(anchor, block, 1)
p.write_text(s)

# changelog
p = root / 'CHANGELOG.md'
s = p.read_text()
idx = s.index('## 1.4.1 — Book Customization')
entry = '''## 1.5.0 — Dynamic Member Book\n\n- Added optional PlaceholderAPI integration for dynamic Member Book name and lore.\n- Added built-in placeholders `%player%`, `%uuid%`, `%world%`, `%ping%`, and `%online%` that work even without PlaceholderAPI.\n- Added lightweight scheduled dynamic refresh; default interval is 200 ticks (10 seconds), with a 40-tick internal minimum.\n- Added `member-book.dynamic.enabled`, `placeholderapi`, `built-in-placeholders`, `refresh-interval-ticks`, `refresh-on-join`, and `refresh-on-world-change`.\n- PlaceholderAPI is a soft dependency; CdrMemberBook remains functional when it is not installed.\n- Dynamic refresh only updates eligible players that already own a Member Book and never bypasses Bedrock-only eligibility or admin recovery suppression.\n- Added `/cdrmemberbook refresh <player>` for manual placeholder/lore refresh.\n- Existing Safety & Recovery and Book Customization PDC identity/protections remain intact after every dynamic refresh.\n- Config migration v6 -> v7 automatically adds dynamic defaults without changing existing name/lore text.\n- Added PlaceholderAPI 2.12.3 as a provided Maven dependency; it is not bundled into the plugin jar.\n- Version bumped to `1.5.0`.\n\n'''
s = s[:idx] + entry + s[idx:]
p.write_text(s)

# README
p = root / 'README.md'
s = p.read_text()
s = s.replace('# CdrMemberBook v1.4.1', '# CdrMemberBook v1.5.0', 1)
s = s.replace('target/CdrMemberBook-1.4.1.jar', 'target/CdrMemberBook-1.5.0.jar')
anchor = '## Book Customization\n'
if anchor in s and '## Dynamic Member Book' not in s:
    section = '''## Dynamic Member Book\n\n`v1.5.0` mendukung placeholder pada `member-book.name` dan setiap baris `member-book.lore`. Placeholder bawaan `%player%`, `%uuid%`, `%world%`, `%ping%`, dan `%online%` bekerja tanpa dependency tambahan. Jika PlaceholderAPI terpasang, placeholder dari expansion lain juga dapat dipakai.\n\n```yaml\nmember-book:\n  name: '&d&lMOONSIGN &f%player%'\n  lore:\n    - '&7Rank: &f%luckperms_prefix%'\n    - '&7Balance: &a%vault_eco_balance_formatted%'\n    - '&7Ping: &f%ping%ms'\n    - '&7Online: &f%online%'\n  dynamic:\n    enabled: true\n    placeholderapi: true\n    built-in-placeholders: true\n    refresh-interval-ticks: 200\n    refresh-on-join: true\n    refresh-on-world-change: true\n```\n\nPlaceholderAPI bersifat optional/soft dependency. Expansion seperti LuckPerms/Vault tetap harus tersedia agar placeholder masing-masing dapat di-resolve. Gunakan `/cdrmemberbook refresh <player>` untuk refresh manual.\n\n'''
    s = s.replace(anchor, section + anchor, 1)
p.write_text(s)
