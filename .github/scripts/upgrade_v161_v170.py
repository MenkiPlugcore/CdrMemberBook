from pathlib import Path
import re
import sys

root = Path('.')
phase = sys.argv[1] if len(sys.argv) > 1 else ''


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)


def write(path, text):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def stability():
    # Version metadata
    p = root / 'pom.xml'
    s = p.read_text()
    s = replace_once(s, '<version>1.6.0</version>', '<version>1.6.1</version>', 'pom version 1.6.1')
    p.write_text(s)

    p = root / 'src/main/resources/plugin.yml'
    s = p.read_text()
    s = replace_once(s, "version: '1.6.0'", "version: '1.6.1'", 'plugin version 1.6.1')
    s = s.replace('usage: /cdrmemberbook <give|remove|fix|refresh> <player>',
                  'usage: /cdrmemberbook <give|remove|fix|refresh|status> <player>')
    p.write_text(s)

    # MemberBookService diagnostics + validation
    p = root / 'src/main/java/id/cadera/memberbook/item/MemberBookService.java'
    s = p.read_text()
    old = '''    public String modeName() {
        return bookMode().name();
    }
'''
    new = '''    public String modeName() {
        return bookMode().name();
    }

    public void validateConfiguration() {
        String rawMode = plugin.getConfig().getString("member-book.mode", "MOVABLE");
        if (!isValidMode(rawMode)) {
            plugin.getLogger().warning("Invalid member-book.mode '" + rawMode
                    + "'. Falling back to MOVABLE. Valid: MOVABLE, LOCKED_HOTBAR, FIXED_SLOT_MOVABLE, NORMAL.");
        }

        int slot = plugin.getConfig().getInt("member-book.hotbar-slot", 8);
        if (slot < 0 || slot > 8) {
            plugin.getLogger().warning("member-book.hotbar-slot=" + slot
                    + " is outside 0-8. Runtime value is clamped to " + reservedSlot() + ".");
        }

        long fixedDelay = plugin.getConfig().getLong("member-book.fixed-slot.return-delay-ticks", 40L);
        if (fixedDelay < 1L) {
            plugin.getLogger().warning("member-book.fixed-slot.return-delay-ticks must be >= 1. Runtime uses 1 tick minimum.");
        }
    }

    public BookStatus inspect(Player player) {
        int inventoryCopies = 0;
        for (ItemStack item : player.getInventory().getContents()) {
            if (isMemberBook(item)) inventoryCopies++;
        }
        boolean cursorBook = isMemberBook(player.getItemOnCursor());
        int externalCopies = 0;
        if (isExternalView(player)) {
            for (ItemStack item : player.getOpenInventory().getTopInventory().getContents()) {
                if (isMemberBook(item)) externalCopies++;
            }
        }
        boolean bedrock = plugin.forms() != null && plugin.forms().isBedrock(player);
        boolean preventDrop = bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.prevent-drop", true);
        return new BookStatus(
                bookMode().name(), isValidMode(plugin.getConfig().getString("member-book.mode", "MOVABLE")),
                isEligibleForBook(player), bedrock, inventoryCopies, cursorBook, externalCopies,
                reservedSlot(), isMemberBook(player.getInventory().getItem(reservedSlot())),
                recoverySuppressed.contains(player.getUniqueId()), recoveryEnabled(),
                preventExternalStorage(), preventDrop,
                fixedSlotReturnPending.contains(player.getUniqueId()), dynamicEnabled());
    }

    private boolean isValidMode(String value) {
        if (value == null || value.isBlank()) return true;
        try {
            BookMode.valueOf(value.trim().toUpperCase());
            return true;
        } catch (IllegalArgumentException ignored) {
            return false;
        }
    }
'''
    s = replace_once(s, old, new, 'mode diagnostics methods')

    enum_marker = '''    private enum BookMode {
        MOVABLE,
        LOCKED_HOTBAR,
        FIXED_SLOT_MOVABLE,
        NORMAL
    }
'''
    record_and_enum = '''    public record BookStatus(
            String mode,
            boolean configuredModeValid,
            boolean eligible,
            boolean bedrock,
            int inventoryCopies,
            boolean cursorBook,
            int externalCopies,
            int reservedSlot,
            boolean bookInReservedSlot,
            boolean recoverySuppressed,
            boolean recoveryEnabled,
            boolean externalStorageProtected,
            boolean dropProtected,
            boolean fixedReturnPending,
            boolean dynamicEnabled) {
        public int visibleCopies() {
            return inventoryCopies + (cursorBook ? 1 : 0) + externalCopies;
        }
    }

    private enum BookMode {
        MOVABLE,
        LOCKED_HOTBAR,
        FIXED_SLOT_MOVABLE,
        NORMAL
    }
'''
    s = replace_once(s, enum_marker, record_and_enum, 'book status record')
    p.write_text(s)

    # Main plugin warnings / version
    p = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
    s = p.read_text()
    s = replace_once(s,
        '        memberBookService.giveToOnlinePlayers();\n        memberBookService.startEnforcement();',
        '        memberBookService.validateConfiguration();\n        memberBookService.giveToOnlinePlayers();\n        memberBookService.startEnforcement();',
        'startup validation')
    s = replace_once(s, 'getLogger().info("CdrMemberBook v1.6.0 enabled.");',
                        'getLogger().info("CdrMemberBook v1.6.1 enabled.");', 'startup version')
    s = replace_once(s,
        '''        if (memberBookService != null) {
            memberBookService.restartEnforcement();
            memberBookService.giveToOnlinePlayers();
        }
''',
        '''        if (memberBookService != null) {
            memberBookService.validateConfiguration();
            memberBookService.restartEnforcement();
            memberBookService.giveToOnlinePlayers();
        }
''', 'reload validation')
    p.write_text(s)

    # Admin status command
    p = root / 'src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'
    s = p.read_text()
    refresh_case = '''            case "refresh" -> {
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
    status_case = refresh_case + '''            case "status" -> {
                MemberBookService.BookStatus status = service.inspect(target);
                sender.sendMessage(Colors.legacy("&dCdrMemberBook Status &8- &f" + target.getName()));
                sender.sendMessage(Colors.legacy("&7Mode: &f" + status.mode()
                        + (status.configuredModeValid() ? "" : " &c(config invalid -> fallback)")));
                sender.sendMessage(Colors.legacy("&7Platform: &f" + (status.bedrock() ? "Bedrock" : "Java")
                        + " &8| &7Eligible: &f" + status.eligible()));
                sender.sendMessage(Colors.legacy("&7Copies: &f" + status.visibleCopies()
                        + " &8(inv=" + status.inventoryCopies() + ", cursor=" + status.cursorBook()
                        + ", external=" + status.externalCopies() + ")"));
                sender.sendMessage(Colors.legacy("&7Reserved slot: &f" + status.reservedSlot()
                        + " &8| &7Book in slot: &f" + status.bookInReservedSlot()));
                sender.sendMessage(Colors.legacy("&7Recovery: &f" + status.recoveryEnabled()
                        + " &8| &7Suppressed: &f" + status.recoverySuppressed()
                        + " &8| &7Fixed return pending: &f" + status.fixedReturnPending()));
                sender.sendMessage(Colors.legacy("&7External protection: &f" + status.externalStorageProtected()
                        + " &8| &7Drop protection: &f" + status.dropProtected()
                        + " &8| &7Dynamic: &f" + status.dynamicEnabled()));
            }
'''
    s = replace_once(s, refresh_case, status_case, 'status command case')
    s = s.replace('&dCdrMemberBook &fv1.5.0 &8- &7Admin Recovery', '&dCdrMemberBook &fv1.6.1 &8- &7Admin Tools')
    s = replace_once(s,
        '        sender.sendMessage(Colors.legacy("&f/" + label + " refresh <player> &8- &7refresh placeholder nama/lore"));\n',
        '        sender.sendMessage(Colors.legacy("&f/" + label + " refresh <player> &8- &7refresh placeholder nama/lore"));\n'
        '        sender.sendMessage(Colors.legacy("&f/" + label + " status <player> &8- &7diagnostic Book Modes + recovery"));\n',
        'status usage')
    s = s.replace('List.of("give", "remove", "fix", "refresh")',
                  'List.of("give", "remove", "fix", "refresh", "status")')
    p.write_text(s)

    # Docs
    p = root / 'CHANGELOG.md'
    s = p.read_text() if p.exists() else '# Changelog\n'
    entry = '''\n## 1.6.1 - Book Modes Stability\n\n- Added `/cdrmemberbook status <player>` diagnostics.\n- Added startup/reload validation for invalid mode, hotbar slot and fixed-slot delay.\n- Hardened Book Modes observability without changing default MOVABLE behavior.\n'''
    if '## 1.6.1 - Book Modes Stability' not in s:
        s = s.replace('# Changelog\n', '# Changelog\n' + entry, 1)
    p.write_text(s)

    p = root / 'README.md'
    if p.exists():
        s = p.read_text().replace('v1.6.0', 'v1.6.1')
        if 'Book Modes Stability' not in s:
            s += '\n\n## Book Modes Stability v1.6.1\n\nUse `/cdrmemberbook status <player>` to inspect active mode, visible copies, reserved slot, recovery suppression, external/drop protection and dynamic refresh state. Invalid Book Mode config values safely fall back to `MOVABLE` and produce a startup/reload warning.\n'
        p.write_text(s)


def tutorial():
    # Version metadata
    p = root / 'pom.xml'
    s = p.read_text()
    s = replace_once(s, '<version>1.6.1</version>', '<version>1.7.0</version>', 'pom version 1.7.0')
    p.write_text(s)

    p = root / 'src/main/resources/plugin.yml'
    s = p.read_text()
    s = replace_once(s, "version: '1.6.1'", "version: '1.7.0'", 'plugin version 1.7.0')
    s = s.replace('usage: /cdrmemberbook <give|remove|fix|refresh|status> <player>',
                  'usage: /cdrmemberbook <give|remove|fix|refresh|status|tutorialreset|tutorialshow> <player>')
    p.write_text(s)

    # Tutorial forms in BedrockFormService
    p = root / 'src/main/java/id/cadera/memberbook/form/BedrockFormService.java'
    s = p.read_text()
    marker = '''    public void showMainMenu(Player player) {
        showConfiguredMenu(player, "main");
    }
'''
    addition = marker + '''
    public void showFirstJoinTutorial(Player player, Runnable onComplete) {
        if (!player.isOnline()) return;
        showTutorialWelcome(player, onComplete == null ? () -> { } : onComplete);
    }

    private void showTutorialWelcome(Player player, Runnable onComplete) {
        String base = "tutorial.welcome.";
        SimpleForm.Builder builder = SimpleForm.builder()
                .title(plugin.formatMenuText(plugin.getConfig().getString(base + "title", "&d&lMOONSIGN"), player))
                .content(plugin.formatMenuText(plugin.getConfig().getString(base + "content",
                        "&fSelamat datang! Member Book adalah pusat menu pribadi kamu."), player));
        addButton(builder, plugin.getConfig().getString(base + "button", "Lanjut"), "player", "textures/items/book_written");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (player.isOnline()) showTutorialFeatures(player, onComplete);
        })).build());
    }

    private void showTutorialFeatures(Player player, Runnable onComplete) {
        String base = "tutorial.features.";
        SimpleForm.Builder builder = SimpleForm.builder()
                .title(plugin.formatMenuText(plugin.getConfig().getString(base + "title", "Fitur Member Book"), player))
                .content(plugin.formatMenuText(plugin.getConfig().getString(base + "content",
                        "&fGunakan Member Book untuk Home, TPA, Transfer, Barter, Shop dan fitur server lainnya."), player));
        addButton(builder, plugin.getConfig().getString(base + "button", "Lanjut"), "player", "textures/items/compass_item");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (player.isOnline()) showTutorialReady(player, onComplete);
        })).build());
    }

    private void showTutorialReady(Player player, Runnable onComplete) {
        String base = "tutorial.ready.";
        SimpleForm.Builder builder = SimpleForm.builder()
                .title(plugin.formatMenuText(plugin.getConfig().getString(base + "title", "Siap Bermain"), player))
                .content(plugin.formatMenuText(plugin.getConfig().getString(base + "content",
                        "&fKlik kanan Member Book kapan saja untuk membuka Menu Member."), player));
        addButton(builder, plugin.getConfig().getString(base + "button", "Mulai"), "player", "textures/items/emerald");
        send(player, builder.validResultHandler(response -> sync(() -> {
            if (!player.isOnline()) return;
            onComplete.run();
            if (plugin.getConfig().getBoolean("tutorial.open-menu-after-complete", true)) {
                showMainMenu(player);
            }
        })).build());
    }
'''
    s = replace_once(s, marker, addition, 'tutorial form insertion')
    p.write_text(s)

    # Persistent tutorial service
    tutorial_java = '''package id.cadera.memberbook.tutorial;

import id.cadera.memberbook.CdrMemberBookPlugin;
import org.bukkit.Bukkit;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;

import java.io.File;
import java.io.IOException;
import java.time.Instant;
import java.util.UUID;

public final class FirstJoinTutorialService implements Listener {
    private final CdrMemberBookPlugin plugin;
    private final File file;
    private final YamlConfiguration data;

    public FirstJoinTutorialService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.file = new File(plugin.getDataFolder(), "tutorial-data.yml");
        this.data = YamlConfiguration.loadConfiguration(file);
    }

    public boolean completed(UUID uuid) {
        return data.getBoolean(path(uuid, "completed"), false);
    }

    public boolean eligible(UUID uuid) {
        return data.getBoolean(path(uuid, "eligible"), false);
    }

    public void reset(Player player) {
        UUID uuid = player.getUniqueId();
        data.set(path(uuid, "eligible"), true);
        data.set(path(uuid, "completed"), false);
        data.set(path(uuid, "completed-at"), null);
        save();
    }

    public void showNow(Player player) {
        if (!canShow(player)) return;
        show(player);
    }

    public boolean canShow(Player player) {
        if (!plugin.getConfig().getBoolean("tutorial.enabled", true)) return false;
        if (plugin.forms() == null || !plugin.forms().isBedrock(player)) return false;
        return player.isOnline();
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        Player player = event.getPlayer();
        if (!plugin.getConfig().getBoolean("tutorial.enabled", true)) return;
        if (plugin.getConfig().getBoolean("tutorial.bedrock-only", true)
                && (plugin.forms() == null || !plugin.forms().isBedrock(player))) return;

        UUID uuid = player.getUniqueId();
        boolean firstJoin = !player.hasPlayedBefore();
        boolean showExisting = plugin.getConfig().getBoolean("tutorial.show-to-existing-unseen", false);

        if (!eligible(uuid)) {
            if (firstJoin || showExisting) {
                data.set(path(uuid, "eligible"), true);
                save();
            } else {
                return;
            }
        }
        if (completed(uuid)) return;

        long delay = Math.max(1L, plugin.getConfig().getLong("tutorial.delay-ticks", 60L));
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline() && !completed(uuid) && canShow(player)) show(player);
        }, delay);
    }

    private void show(Player player) {
        plugin.forms().showFirstJoinTutorial(player, () -> markCompleted(player));
    }

    private void markCompleted(Player player) {
        UUID uuid = player.getUniqueId();
        data.set(path(uuid, "eligible"), true);
        data.set(path(uuid, "completed"), true);
        data.set(path(uuid, "completed-at"), Instant.now().toString());
        save();
        plugin.message(player, "tutorial-completed");
    }

    private String path(UUID uuid, String key) {
        return "players." + uuid + "." + key;
    }

    private void save() {
        try {
            data.save(file);
        } catch (IOException exception) {
            plugin.getLogger().warning("Could not save tutorial-data.yml: " + exception.getMessage());
        }
    }
}
'''
    write('src/main/java/id/cadera/memberbook/tutorial/FirstJoinTutorialService.java', tutorial_java)

    # Main plugin integration + config migration
    p = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
    s = p.read_text()
    s = replace_once(s,
        'import id.cadera.memberbook.tp.ToggleStore;\n',
        'import id.cadera.memberbook.tp.ToggleStore;\nimport id.cadera.memberbook.tutorial.FirstJoinTutorialService;\n',
        'tutorial import')
    s = replace_once(s,
        '    private EssentialsHomeService essentialsHomeService;\n',
        '    private EssentialsHomeService essentialsHomeService;\n    private FirstJoinTutorialService tutorialService;\n',
        'tutorial field')
    s = replace_once(s,
        '''        if (Bukkit.getPluginManager().isPluginEnabled("PlaceholderAPI")) {
            getLogger().info("PlaceholderAPI detected: Dynamic Member Book placeholders enabled.");
        } else {
            getLogger().info("PlaceholderAPI not detected: Dynamic Member Book will use built-in placeholders only.");
        }

        registerCommands();
''',
        '''        if (Bukkit.getPluginManager().isPluginEnabled("PlaceholderAPI")) {
            getLogger().info("PlaceholderAPI detected: Dynamic Member Book placeholders enabled.");
        } else {
            getLogger().info("PlaceholderAPI not detected: Dynamic Member Book will use built-in placeholders only.");
        }

        tutorialService = new FirstJoinTutorialService(this);
        registerCommands();
''', 'tutorial service init')
    s = replace_once(s,
        '        Bukkit.getPluginManager().registerEvents(memberBookService, this);\n',
        '        Bukkit.getPluginManager().registerEvents(memberBookService, this);\n        Bukkit.getPluginManager().registerEvents(tutorialService, this);\n',
        'tutorial listener register')
    s = replace_once(s, 'getLogger().info("CdrMemberBook v1.6.1 enabled.");',
                        'getLogger().info("CdrMemberBook v1.7.0 enabled.");', 'version 1.7.0')

    migration = '''        if (configVersion < 11) {
            if (!getConfig().isSet("member-book.mode")) {
                getConfig().set("member-book.mode",
                        getConfig().getBoolean("member-book.permanent-hotbar", false)
                                ? "LOCKED_HOTBAR" : "MOVABLE");
            }
            getConfig().set("member-book.fixed-slot.return-delay-ticks", 40L);
        }

        getConfig().set("config-version", 11);
'''
    migration_new = '''        if (configVersion < 11) {
            if (!getConfig().isSet("member-book.mode")) {
                getConfig().set("member-book.mode",
                        getConfig().getBoolean("member-book.permanent-hotbar", false)
                                ? "LOCKED_HOTBAR" : "MOVABLE");
            }
            getConfig().set("member-book.fixed-slot.return-delay-ticks", 40L);
        }

        if (configVersion < 12) {
            getConfig().set("tutorial.enabled", true);
            getConfig().set("tutorial.bedrock-only", true);
            getConfig().set("tutorial.show-to-existing-unseen", false);
            getConfig().set("tutorial.delay-ticks", 60L);
            getConfig().set("tutorial.open-menu-after-complete", true);
        }

        getConfig().set("config-version", 12);
'''
    s = replace_once(s, migration, migration_new, 'tutorial migration')
    getter_marker = '''    public EssentialsHomeService homes() {
        return essentialsHomeService;
    }
'''
    getter_new = getter_marker + '''
    public FirstJoinTutorialService tutorial() {
        return tutorialService;
    }
'''
    s = replace_once(s, getter_marker, getter_new, 'tutorial getter')
    p.write_text(s)

    # Admin tutorial reset/show
    p = root / 'src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'
    s = p.read_text()
    status_tail = '''            case "status" -> {
                MemberBookService.BookStatus status = service.inspect(target);
                sender.sendMessage(Colors.legacy("&dCdrMemberBook Status &8- &f" + target.getName()));
                sender.sendMessage(Colors.legacy("&7Mode: &f" + status.mode()
                        + (status.configuredModeValid() ? "" : " &c(config invalid -> fallback)")));
                sender.sendMessage(Colors.legacy("&7Platform: &f" + (status.bedrock() ? "Bedrock" : "Java")
                        + " &8| &7Eligible: &f" + status.eligible()));
                sender.sendMessage(Colors.legacy("&7Copies: &f" + status.visibleCopies()
                        + " &8(inv=" + status.inventoryCopies() + ", cursor=" + status.cursorBook()
                        + ", external=" + status.externalCopies() + ")"));
                sender.sendMessage(Colors.legacy("&7Reserved slot: &f" + status.reservedSlot()
                        + " &8| &7Book in slot: &f" + status.bookInReservedSlot()));
                sender.sendMessage(Colors.legacy("&7Recovery: &f" + status.recoveryEnabled()
                        + " &8| &7Suppressed: &f" + status.recoverySuppressed()
                        + " &8| &7Fixed return pending: &f" + status.fixedReturnPending()));
                sender.sendMessage(Colors.legacy("&7External protection: &f" + status.externalStorageProtected()
                        + " &8| &7Drop protection: &f" + status.dropProtected()
                        + " &8| &7Dynamic: &f" + status.dynamicEnabled()));
            }
'''
    tutorial_cases = status_tail + '''            case "tutorialreset" -> {
                plugin.tutorial().reset(target);
                sender.sendMessage(Colors.legacy("&aFirst Join Tutorial di-reset untuk &f" + target.getName()
                        + "&a. Tutorial akan tersedia lagi pada join berikutnya."));
            }
            case "tutorialshow" -> {
                if (!plugin.tutorial().canShow(target)) {
                    sender.sendMessage(Colors.legacy("&eTutorial native hanya bisa ditampilkan ke player Bedrock/Floodgate yang online saat fitur aktif."));
                    return true;
                }
                plugin.tutorial().showNow(target);
                sender.sendMessage(Colors.legacy("&aFirst Join Tutorial ditampilkan ke &f" + target.getName() + "&a."));
            }
'''
    s = replace_once(s, status_tail, tutorial_cases, 'tutorial admin cases')
    s = s.replace('&dCdrMemberBook &fv1.6.1 &8- &7Admin Tools', '&dCdrMemberBook &fv1.7.0 &8- &7Admin Tools')
    s = replace_once(s,
        '        sender.sendMessage(Colors.legacy("&f/" + label + " status <player> &8- &7diagnostic Book Modes + recovery"));\n',
        '        sender.sendMessage(Colors.legacy("&f/" + label + " status <player> &8- &7diagnostic Book Modes + recovery"));\n'
        '        sender.sendMessage(Colors.legacy("&f/" + label + " tutorialreset <player> &8- &7reset tutorial player"));\n'
        '        sender.sendMessage(Colors.legacy("&f/" + label + " tutorialshow <player> &8- &7paksa tampilkan tutorial Bedrock"));\n',
        'tutorial usage')
    s = s.replace('List.of("give", "remove", "fix", "refresh", "status")',
                  'List.of("give", "remove", "fix", "refresh", "status", "tutorialreset", "tutorialshow")')
    p.write_text(s)

    # Config tutorial block + version
    p = root / 'src/main/resources/config.yml'
    s = p.read_text()
    s = replace_once(s, '# CdrMemberBook v1.6.0\nconfig-version: 11', '# CdrMemberBook v1.7.0\nconfig-version: 12', 'config header')
    tutorial_block = '''# First Join Tutorial v1.7.0
# Hanya player baru yang ditandai eligible secara default. Jika form ditutup sebelum selesai,
# status eligible disimpan sehingga tutorial akan muncul lagi pada login berikutnya.
tutorial:
  enabled: true
  bedrock-only: true
  # false = player lama saat plugin di-update tidak otomatis diberi tutorial.
  show-to-existing-unseen: false
  # 60 ticks = 3 detik setelah join agar Floodgate/client sudah siap menerima form.
  delay-ticks: 60
  open-menu-after-complete: true

  welcome:
    title: '&d&lMOONSIGN'
    content: '&fSelamat datang, &d%player%&f!\\n&7Member Book adalah pusat menu pribadi kamu di server.'
    button: 'Lanjut'

  features:
    title: '&dMember Book'
    content: '&fDari Member Book kamu bisa membuka Home, TPA, Transfer, Barter, Shop, Party dan fitur server lainnya tanpa menghafal banyak command.'
    button: 'Lanjut'

  ready:
    title: '&aSiap Bermain'
    content: '&fKlik kanan Member Book kapan saja untuk membuka Menu Member.\\n&7Kalau buku hilang pada mode aman, sistem recovery akan membantu memulihkannya.'
    button: 'Mulai'

'''
    insert_at = '# Native integrations used by the Bedrock click-only flows.\n'
    s = replace_once(s, insert_at, tutorial_block + insert_at, 'tutorial config block')
    s = replace_once(s,
        "  home: textures/items/bed_red\n",
        "  home: textures/items/bed_red\n  tutorial: textures/items/book_written\n",
        'tutorial icon config')
    s = replace_once(s,
        "  home-preset-no-permission: '&cKamu tidak punya izin untuk menggunakan preset",
        "  tutorial-completed: '&aTutorial selesai. Selamat bermain!'\n  home-preset-no-permission: '&cKamu tidak punya izin untuk menggunakan preset",
        'tutorial completed message')
    p.write_text(s)

    # Changelog/README
    p = root / 'CHANGELOG.md'
    s = p.read_text() if p.exists() else '# Changelog\n'
    entry = '''\n## 1.7.0 - First Join Tutorial\n\n- Added native three-step Bedrock first-join tutorial.\n- Tutorial completion/eligibility persists per UUID in `tutorial-data.yml`.\n- Existing players are not shown the tutorial by default.\n- Closing before completion keeps first-join players eligible for the next login.\n- Added `/cdrmemberbook tutorialreset <player>` and `/cdrmemberbook tutorialshow <player>`.\n'''
    if '## 1.7.0 - First Join Tutorial' not in s:
        s = s.replace('# Changelog\n', '# Changelog\n' + entry, 1)
    p.write_text(s)

    p = root / 'README.md'
    if p.exists():
        s = p.read_text().replace('v1.6.1', 'v1.7.0')
        if 'First Join Tutorial v1.7.0' not in s:
            s += '''\n\n## First Join Tutorial v1.7.0\n\nNew Bedrock players receive a native three-step tutorial after join. Completion is persisted in `plugins/CdrMemberBook/tutorial-data.yml`. Existing players are skipped by default (`tutorial.show-to-existing-unseen: false`). Admins can test/reset with `/cdrmemberbook tutorialshow <player>` and `/cdrmemberbook tutorialreset <player>`.\n'''
        p.write_text(s)


if phase == 'stability':
    stability()
elif phase == 'tutorial':
    tutorial()
else:
    raise SystemExit('usage: upgrade_v161_v170.py stability|tutorial')
