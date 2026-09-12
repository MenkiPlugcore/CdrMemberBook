package id.cadera.memberbook.command;

import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import id.cadera.memberbook.CdrMemberBookPlugin;
import id.cadera.memberbook.tp.TeleportMode;

import java.util.List;

public final class TeleportCommands implements CommandExecutor, TabCompleter {
    private final CdrMemberBookPlugin plugin;

    public TeleportCommands(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    @Override
    public boolean onCommand(@NotNull CommandSender sender, @NotNull Command command,
                             @NotNull String label, @NotNull String[] args) {
        if (!(sender instanceof Player player)) {
            sender.sendMessage("This command is player-only.");
            return true;
        }

        switch (command.getName().toLowerCase()) {
            case "tpa", "tpahere" -> {
                if (args.length != 1) return false;
                Player target = Bukkit.getPlayerExact(args[0]);
                if (target == null) {
                    plugin.message(player, "player-not-found");
                    return true;
                }
                plugin.requests().create(player, target,
                        command.getName().equalsIgnoreCase("tpahere")
                                ? TeleportMode.TARGET_TO_REQUESTER : TeleportMode.TO_TARGET);
                return true;
            }
            case "tpaccept" -> {
                plugin.requests().accept(player);
                return true;
            }
            case "tpdeny" -> {
                plugin.requests().deny(player);
                return true;
            }
            case "tptoggle" -> {
                boolean disabled = plugin.requests().toggles().toggle(player.getUniqueId());
                plugin.message(player, disabled ? "toggle-off" : "toggle-on");
                return true;
            }
            default -> {
                return false;
            }
        }
    }

    @Override
    public @Nullable List<String> onTabComplete(@NotNull CommandSender sender, @NotNull Command command,
                                                 @NotNull String alias, @NotNull String[] args) {
        if ((command.getName().equalsIgnoreCase("tpa") || command.getName().equalsIgnoreCase("tpahere"))
                && args.length == 1) {
            String prefix = args[0].toLowerCase();
            return Bukkit.getOnlinePlayers().stream()
                    .map(Player::getName)
                    .filter(name -> !name.equalsIgnoreCase(sender.getName()))
                    .filter(name -> name.toLowerCase().startsWith(prefix))
                    .sorted(String.CASE_INSENSITIVE_ORDER)
                    .toList();
        }
        return List.of();
    }
}
