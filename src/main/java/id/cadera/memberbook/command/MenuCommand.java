package id.cadera.memberbook.command;

import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.util.Colors;

import java.util.List;

public final class MenuCommand implements CommandExecutor, TabCompleter {
    private final CdrMemberBookPlugin plugin;

    public MenuCommand(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                             @NotNull String label, @NotNull String[] args) {
        if (args.length > 0 && args[0].equalsIgnoreCase("reload")) {
            if (!sender.hasPermission("cdrmemberbook.admin.reload")) {
                if (sender instanceof Player player) plugin.message(player, "no-permission");
                else sender.sendMessage("You do not have permission.");
                return true;
            }
            plugin.reloadCdrMemberBookConfig();
            if (sender instanceof Player player) plugin.message(player, "config-reloaded");
            else sender.sendMessage(Colors.legacy("&aCdrMemberBook config reloaded."));
            return true;
        }

        if (!(sender instanceof Player player)) {
            sender.sendMessage("This command is player-only. Use /menu reload to reload the config.");
            return true;
        }
        plugin.openMenu(player);
        return true;
    }

    @Override
    public @Nullable List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                                 @NotNull String alias, @NotNull String[] args) {
        if (args.length == 1 && sender.hasPermission("cdrmemberbook.admin.reload")) {
            if ("reload".startsWith(args[0].toLowerCase())) return List.of("reload");
        }
        return List.of();
    }
}
