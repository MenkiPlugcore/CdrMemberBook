from pathlib import Path

root = Path('.')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)

# versions
p = root/'pom.xml'; s=p.read_text(); s=replace_once(s,'<version>1.7.0</version>','<version>1.8.0</version>','pom version'); p.write_text(s)
p = root/'src/main/resources/plugin.yml'; s=p.read_text(); s=replace_once(s,"version: '1.7.0'","version: '1.8.0'",'plugin version')
s=replace_once(s,'  moonsignmenu.admin.memberbook:\n    default: op\n','  moonsignmenu.admin.memberbook:\n    default: op\n  moonsignmenu.staff.report:\n    default: op\n','report staff permission')
p.write_text(s)

# MenuConfigService
p=root/'src/main/java/id/cadera/memberbook/menu/MenuConfigService.java'; s=p.read_text()
s=replace_once(s,
'''                        button.getString("permission", ""),
                        button.getInt("order", 100),
                        button.getStringList("lore")
''',
'''                        button.getString("permission", ""),
                        button.getInt("order", 100),
                        button.getStringList("lore"),
                        button.getStringList("requires-plugins"),
                        button.getString("requires-command", ""),
                        button.getBoolean("auto-detect-command", true)
''','button parser')
s=replace_once(s,
'''    public List<MenuButton> visibleButtons(MenuDefinition menu, Player player) {
        boolean hideWithoutPermission = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
        if (!hideWithoutPermission) return menu.buttons();
        return menu.buttons().stream().filter(button -> canUse(player, button)).toList();
    }

    public boolean canUse(Player player, MenuButton button) {
        String permission = button.permission();
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }
''',
'''    public List<MenuButton> visibleButtons(MenuDefinition menu, Player player) {
        boolean hideWithoutPermission = plugin.getConfig().getBoolean("menu.hide-buttons-without-permission", true);
        boolean hideUnavailable = plugin.getConfig().getBoolean("menu.hide-unavailable-buttons", true);
        return menu.buttons().stream()
                .filter(button -> !hideWithoutPermission || canUse(player, button))
                .filter(button -> !hideUnavailable || isAvailable(player, button))
                .toList();
    }

    public boolean canUse(Player player, MenuButton button) {
        String permission = button.permission();
        return permission == null || permission.isBlank() || player.hasPermission(permission);
    }

    public boolean isAvailable(Player player, MenuButton button) {
        for (String pluginName : button.requiredPlugins()) {
            if (pluginName == null || pluginName.isBlank()) continue;
            if (!plugin.getServer().getPluginManager().isPluginEnabled(pluginName.trim())) return false;
        }

        if (button.requiredCommand() != null && !button.requiredCommand().isBlank()
                && !commandAvailable(button.requiredCommand())) return false;

        String type = button.type() == null ? "command" : button.type().toLowerCase(Locale.ROOT);
        return switch (type) {
            case "teleport", "submenu", "close" -> true;
            case "homes" -> plugin.homes() != null && plugin.homes().available();
            case "pay" -> commandAvailable(plugin.getConfig().getString(
                    "integrations.pay.command", "pay %target% %amount%"));
            case "trade" -> plugin.getServer().getPluginManager().isPluginEnabled("AxTrade")
                    && commandAvailable(plugin.getConfig().getString(
                    "integrations.axtrade.send-command", "axtrade %target%"));
            case "report" -> {
                boolean nativeBedrock = plugin.reports() != null && plugin.reports().enabled()
                        && plugin.forms() != null && plugin.forms().isBedrock(player);
                yield nativeBedrock || commandAvailable(button.command());
            }
            case "command" -> !plugin.getConfig().getBoolean("menu.auto-detect-command-dependencies", true)
                    || !button.autoDetectCommand() || commandAvailable(button.command());
            default -> true;
        };
    }

    public boolean commandAvailable(String template) {
        if (template == null || template.isBlank()) return false;
        String normalized = template.trim();
        if (normalized.startsWith("/")) normalized = normalized.substring(1);
        int space = normalized.indexOf(' ');
        String root = space < 0 ? normalized : normalized.substring(0, space);
        if (root.isBlank() || root.contains("%")) return false;
        return plugin.getServer().getCommandMap().getCommand(root.toLowerCase(Locale.ROOT)) != null;
    }
''','availability methods')
s=replace_once(s,
'''            String permission,
            int order,
            List<String> lore
    ) {}
''',
'''            String permission,
            int order,
            List<String> lore,
            List<String> requiredPlugins,
            String requiredCommand,
            boolean autoDetectCommand
    ) {}
''','record fields')
p.write_text(s)

# ReportService
report_java='''package id.cadera.memberbook.report;

import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.util.Colors;
import org.bukkit.Bukkit;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;

import java.io.File;
import java.io.IOException;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public final class ReportService {
    private final CdrMemberBookPlugin plugin;
    private final File file;
    private final YamlConfiguration data;
    private final Map<UUID, Long> cooldownUntil = new HashMap<>();

    public ReportService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.file = new File(plugin.getDataFolder(), "reports.yml");
        this.data = YamlConfiguration.loadConfiguration(file);
    }

    public boolean enabled() {
        return plugin.getConfig().getBoolean("integrations.report.enabled", true);
    }

    public SubmitResult submit(Player reporter, Player target, String rawReason) {
        if (!enabled()) return new SubmitResult(false, 0, 0, "disabled");
        if (reporter.getUniqueId().equals(target.getUniqueId())) return new SubmitResult(false, 0, 0, "self");

        String reason = rawReason == null ? "" : rawReason.trim();
        int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
        int max = Math.max(min, plugin.getConfig().getInt("integrations.report.max-reason-length", 200));
        if (reason.length() < min) return new SubmitResult(false, 0, 0, "short");
        if (reason.length() > max) reason = reason.substring(0, max);

        long now = System.currentTimeMillis();
        long until = cooldownUntil.getOrDefault(reporter.getUniqueId(), 0L);
        if (until > now) {
            long seconds = Math.max(1L, (until - now + 999L) / 1000L);
            return new SubmitResult(false, 0, seconds, "cooldown");
        }

        int id = Math.max(1, data.getInt("next-id", 1));
        String base = "reports." + id + ".";
        data.set(base + "created-at", Instant.now().toString());
        data.set(base + "reporter.name", reporter.getName());
        data.set(base + "reporter.uuid", reporter.getUniqueId().toString());
        data.set(base + "target.name", target.getName());
        data.set(base + "target.uuid", target.getUniqueId().toString());
        data.set(base + "reason", reason);
        data.set(base + "world", reporter.getWorld().getName());
        data.set(base + "location.x", reporter.getLocation().getBlockX());
        data.set(base + "location.y", reporter.getLocation().getBlockY());
        data.set(base + "location.z", reporter.getLocation().getBlockZ());
        data.set("next-id", id + 1);
        save();

        long cooldown = Math.max(0L, plugin.getConfig().getLong("integrations.report.cooldown-seconds", 60L));
        if (cooldown > 0L) cooldownUntil.put(reporter.getUniqueId(), now + cooldown * 1000L);

        notifyStaff(id, reporter, target, reason);
        runConsoleHook(id, reporter, target, reason);
        plugin.getLogger().info("Report #" + id + ": " + reporter.getName() + " -> " + target.getName() + " | " + reason);
        return new SubmitResult(true, id, 0, "ok");
    }

    private void notifyStaff(int id, Player reporter, Player target, String reason) {
        String permission = plugin.getConfig().getString("integrations.report.staff-permission", "moonsignmenu.staff.report");
        String message = "&8[&cREPORT #" + id + "&8] &f" + reporter.getName() + " &7melaporkan &f"
                + target.getName() + "&7: &f" + reason;
        for (Player online : Bukkit.getOnlinePlayers()) {
            if (permission == null || permission.isBlank() || online.hasPermission(permission)) {
                online.sendMessage(Colors.legacy(message));
            }
        }
    }

    private void runConsoleHook(int id, Player reporter, Player target, String reason) {
        String template = plugin.getConfig().getString("integrations.report.console-command", "");
        if (template == null || template.isBlank()) return;
        String command = template
                .replace("%id%", Integer.toString(id))
                .replace("%reporter%", reporter.getName())
                .replace("%target%", target.getName())
                .replace("%reason%", reason.replace('\\n', ' '));
        if (command.startsWith("/")) command = command.substring(1);
        Bukkit.dispatchCommand(Bukkit.getConsoleSender(), command);
    }

    private void save() {
        try {
            data.save(file);
        } catch (IOException exception) {
            plugin.getLogger().warning("Could not save reports.yml: " + exception.getMessage());
        }
    }

    public record SubmitResult(boolean success, int id, long waitSeconds, String reasonCode) { }
}
'''
write_path=root/'src/main/java/id/cadera/memberbook/report/ReportService.java'; write_path.parent.mkdir(parents=True,exist_ok=True); write_path.write_text(report_java)

# main plugin integration
p=root/'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=p.read_text()
s=replace_once(s,'import id.cadera.memberbook.menu.MenuConfigService.MenuButton;\n','import id.cadera.memberbook.menu.MenuConfigService.MenuButton;\nimport id.cadera.memberbook.report.ReportService;\n','report import')
s=replace_once(s,'    private FirstJoinTutorialService tutorialService;\n','    private FirstJoinTutorialService tutorialService;\n    private ReportService reportService;\n','report field')
s=replace_once(s,'        memberBookService = new MemberBookService(this);\n','        memberBookService = new MemberBookService(this);\n        reportService = new ReportService(this);\n','report init')
s=replace_once(s,'        getLogger().info("CdrMemberBook v1.7.0 enabled.");','        getLogger().info("CdrMemberBook v1.8.0 enabled.");','startup version')
s=replace_once(s,
'''        if (configVersion < 12) {
            getConfig().set("tutorial.enabled", true);
            getConfig().set("tutorial.bedrock-only", true);
            getConfig().set("tutorial.show-to-existing-unseen", false);
            getConfig().set("tutorial.delay-ticks", 60L);
            getConfig().set("tutorial.open-menu-after-complete", true);
        }

        getConfig().set("config-version", 12);
''',
'''        if (configVersion < 12) {
            getConfig().set("tutorial.enabled", true);
            getConfig().set("tutorial.bedrock-only", true);
            getConfig().set("tutorial.show-to-existing-unseen", false);
            getConfig().set("tutorial.delay-ticks", 60L);
            getConfig().set("tutorial.open-menu-after-complete", true);
        }

        if (configVersion < 13) {
            getConfig().set("menu.hide-unavailable-buttons", true);
            getConfig().set("menu.auto-detect-command-dependencies", true);
            getConfig().set("integrations.report.enabled", true);
            getConfig().set("integrations.report.cooldown-seconds", 60L);
            getConfig().set("integrations.report.min-reason-length", 3);
            getConfig().set("integrations.report.max-reason-length", 200);
            getConfig().set("integrations.report.staff-permission", "moonsignmenu.staff.report");
            getConfig().set("integrations.report.console-command", "");
            migrateSpecialButton("report", "report", "report", "report");
        }

        getConfig().set("config-version", 13);
''','migration 13')
s=replace_once(s,
'''    public EssentialsHomeService homes() {
        return essentialsHomeService;
    }
''',
'''    public EssentialsHomeService homes() {
        return essentialsHomeService;
    }

    public ReportService reports() {
        return reportService;
    }
''','report accessor')
s=replace_once(s,
'''    public void executeMenuCommand(Player player, MenuButton button) {
        if (!menuConfigService.canUse(player, button)) {
            message(player, "no-permission");
            return;
        }
''',
'''    public void executeMenuCommand(Player player, MenuButton button) {
        if (!menuConfigService.canUse(player, button)) {
            message(player, "no-permission");
            return;
        }
        if (!menuConfigService.isAvailable(player, button)) {
            message(player, "feature-unavailable");
            return;
        }
''','execute availability')
p.write_text(s)

# Bedrock native report flow
p=root/'src/main/java/id/cadera/memberbook/form/BedrockFormService.java'; s=p.read_text()
s=replace_once(s,'import id.cadera.memberbook.menu.MenuConfigService.MenuDefinition;\n','import id.cadera.memberbook.menu.MenuConfigService.MenuDefinition;\nimport id.cadera.memberbook.report.ReportService;\n','report form import')
s=replace_once(s,
'''        if (!plugin.menus().canUse(player, button)) {
            plugin.message(player, "no-permission");
            return;
        }

        switch (button.type().toLowerCase(Locale.ROOT)) {
''',
'''        if (!plugin.menus().canUse(player, button)) {
            plugin.message(player, "no-permission");
            return;
        }
        if (!plugin.menus().isAvailable(player, button)) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, menu.id());
            return;
        }

        switch (button.type().toLowerCase(Locale.ROOT)) {
''','form availability')
s=replace_once(s,'            case "trade" -> showTradeMenu(player, menu.id());\n','            case "trade" -> showTradeMenu(player, menu.id());\n            case "report" -> showReportPlayerSelect(player, menu.id());\n','report switch')
insert_before='''    private void showTradeMenu(Player player, String returnMenuId) {
'''
report_methods='''    private void showReportPlayerSelect(Player player, String returnMenuId) {
        List<PlayerChoice> choices = onlineTargets(player);
        SimpleForm.Builder builder = SimpleForm.builder()
                .title("Lapor Player")
                .content(choices.isEmpty() ? "Tidak ada player lain yang online." : "Pilih player yang ingin dilaporkan.");
        for (PlayerChoice choice : choices) addButton(builder, choice.name(), "player", "textures/items/name_tag");
        addButton(builder, "Kembali", "back", "textures/items/arrow");
        int backIndex = choices.size();
        send(player, builder.validResultHandler(response -> sync(() -> {
            int selected = response.clickedButtonId();
            if (selected == backIndex) {
                showConfiguredMenu(player, returnMenuId);
                return;
            }
            if (selected < 0 || selected >= choices.size()) return;
            Player target = Bukkit.getPlayer(choices.get(selected).uuid());
            if (target == null) {
                plugin.message(player, "player-not-found");
                showReportPlayerSelect(player, returnMenuId);
                return;
            }
            showReportReasonForm(player, target, returnMenuId);
        })).build());
    }

    private void showReportReasonForm(Player player, Player target, String returnMenuId) {
        CustomForm form = CustomForm.builder()
                .title("Lapor " + target.getName())
                .input("Alasan laporan", "contoh: grief, cheat, toxic", "")
                .closedOrInvalidResultHandler(() -> sync(() -> showReportPlayerSelect(player, returnMenuId)))
                .validResultHandler(response -> sync(() -> {
                    String reason = response.asInput(0);
                    int min = Math.max(1, plugin.getConfig().getInt("integrations.report.min-reason-length", 3));
                    if (reason == null || reason.trim().length() < min) {
                        plugin.message(player, "report-reason-too-short", "%min%", Integer.toString(min));
                        showReportReasonForm(player, target, returnMenuId);
                        return;
                    }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) {
                        plugin.message(player, "player-not-found");
                        showReportPlayerSelect(player, returnMenuId);
                        return;
                    }
                    showReportConfirm(player, currentTarget, reason.trim(), returnMenuId);
                }))
                .build();
        send(player, form);
    }

    private void showReportConfirm(Player player, Player target, String reason, String returnMenuId) {
        ModalForm form = ModalForm.builder()
                .title("Konfirmasi Laporan")
                .content("Laporkan " + target.getName() + "?\\n\\nAlasan: " + reason)
                .button1("KIRIM LAPORAN")
                .button2("KEMBALI")
                .validResultHandler(response -> sync(() -> {
                    if (!response.clickedFirst()) {
                        showReportReasonForm(player, target, returnMenuId);
                        return;
                    }
                    Player currentTarget = Bukkit.getPlayer(target.getUniqueId());
                    if (currentTarget == null) {
                        plugin.message(player, "player-not-found");
                        showReportPlayerSelect(player, returnMenuId);
                        return;
                    }
                    ReportService.SubmitResult result = plugin.reports().submit(player, currentTarget, reason);
                    if (result.success()) {
                        plugin.message(player, "report-sent", "%id%", Integer.toString(result.id()),
                                "%player%", currentTarget.getName());
                        showConfiguredMenu(player, returnMenuId);
                    } else if ("cooldown".equals(result.reasonCode())) {
                        plugin.message(player, "report-cooldown", "%seconds%", Long.toString(result.waitSeconds()));
                        showConfiguredMenu(player, returnMenuId);
                    } else if ("self".equals(result.reasonCode())) {
                        plugin.message(player, "cannot-report-self");
                        showReportPlayerSelect(player, returnMenuId);
                    } else {
                        plugin.message(player, "report-failed");
                        showConfiguredMenu(player, returnMenuId);
                    }
                }))
                .build();
        send(player, form);
    }

'''+insert_before
s=replace_once(s,insert_before,report_methods,'report methods')
p.write_text(s)

# Java menu: availability + report fallback
p=root/'src/main/java/id/cadera/memberbook/gui/JavaMenuService.java'; s=p.read_text()
s=replace_once(s,
'''        if (!plugin.menus().canUse(player, button)) {
            plugin.message(player, "no-permission");
            return;
        }

        switch (button.type().toLowerCase(Locale.ROOT)) {
''',
'''        if (!plugin.menus().canUse(player, button)) {
            plugin.message(player, "no-permission");
            return;
        }
        if (!plugin.menus().isAvailable(player, button)) {
            plugin.message(player, "feature-unavailable");
            showConfiguredMenu(player, holder.menuId(), holder.page());
            return;
        }

        switch (button.type().toLowerCase(Locale.ROOT)) {
''','java availability')
s=s.replace('            case "homes", "pay", "trade" -> {','            case "homes", "pay", "trade", "report" -> {',1)
p.write_text(s)

# config
p=root/'src/main/resources/config.yml'; s=p.read_text()
s=replace_once(s,'# CdrMemberBook v1.7.0\nconfig-version: 12','# CdrMemberBook v1.8.0\nconfig-version: 13','config header')
s=replace_once(s,
'''  axtrade:
    # AxTrade canonical commands. If you changed its aliases, edit these templates.
    send-command: 'axtrade %target%'
    accept-command: 'axtrade accept %target%'
    deny-command: 'axtrade deny %target%'
    toggle-command: 'axtrade toggle'
''',
'''  axtrade:
    # AxTrade canonical commands. If you changed its aliases, edit these templates.
    send-command: 'axtrade %target%'
    accept-command: 'axtrade accept %target%'
    deny-command: 'axtrade deny %target%'
    toggle-command: 'axtrade toggle'

  report:
    # Built-in native Bedrock report flow. Tidak membutuhkan plugin report eksternal.
    enabled: true
    cooldown-seconds: 60
    min-reason-length: 3
    max-reason-length: 200
    staff-permission: 'moonsignmenu.staff.report'
    # Optional hook setelah report tersimpan. Placeholder: %id%, %reporter%, %target%, %reason%.
    console-command: ''
''','report config')
s=replace_once(s,
'''menu:
  hide-buttons-without-permission: true
''',
'''menu:
  hide-buttons-without-permission: true
  # Sembunyikan tombol jika dependency/command penyedianya tidak tersedia.
  hide-unavailable-buttons: true
  # Untuk type: command, command root dicek otomatis. Contoh /bank tidak ada -> tombol Bank hilang.
  auto-detect-command-dependencies: true
''','menu availability config')
s=replace_once(s,
'''      report:
        enabled: true
        name: Lapor
        type: command
        command: report
''',
'''      report:
        enabled: true
        name: Lapor
        type: report
        # Java fallback jika ada plugin eksternal dengan /report. Bedrock memakai report native CdrMemberBook.
        command: report
''','report button type')
s=replace_once(s,
'''  invalid-button-type: '&cTipe tombol &f%type% &ctidak dikenali.'
''',
'''  invalid-button-type: '&cTipe tombol &f%type% &ctidak dikenali.'
  feature-unavailable: '&eFitur ini sedang tidak tersedia karena plugin/command yang dibutuhkan tidak aktif.'
  report-reason-too-short: '&eAlasan laporan minimal &f%min% &ekarakter.'
  report-sent: '&aLaporan &f#%id% &auntuk &f%player% &aberhasil dikirim ke staff.'
  report-cooldown: '&eTunggu &f%seconds%s &esebelum membuat laporan lagi.'
  cannot-report-self: '&cKamu tidak bisa melaporkan diri sendiri.'
  report-failed: '&cLaporan tidak dapat dikirim. Coba lagi atau hubungi staff.'
''','report messages')
p.write_text(s)

# changelog/readme
p=root/'CHANGELOG.md'; s=p.read_text(); entry='''\n## 1.8.0 - Smart Menu Conditions & Native Report\n\n- Menu buttons can auto-hide when their command/dependency is unavailable.\n- Generic command buttons auto-detect their root command, so Bank/Shop/AH/etc do not appear when no provider exists.\n- Homes, Pay and AxTrade buttons validate their integrations before being shown.\n- Added optional per-button `requires-plugins`, `requires-command`, and `auto-detect-command`.\n- Added native Bedrock report flow with player picker, reason input, confirmation, cooldown, staff notification and persistent `reports.yml`.\n- Java keeps `/report` as a fallback only when that command actually exists.\n'''
if '## 1.8.0 - Smart Menu Conditions' not in s: s=s.replace('# Changelog\n','# Changelog\n'+entry,1)
p.write_text(s)
p=root/'README.md'; s=p.read_text().replace('v1.7.0','v1.8.0');
if 'Smart Menu Conditions' not in s: s += '''\n\n## Smart Menu Conditions v1.8.0\n\nButtons are hidden automatically when their backing command or integration is unavailable. Command buttons auto-detect the root command, and optional `requires-plugins`, `requires-command`, and `auto-detect-command` fields are supported per button. Bedrock `type: report` uses CdrMemberBook's native report flow and stores reports in `plugins/CdrMemberBook/reports.yml`.\n'''
p.write_text(s)
