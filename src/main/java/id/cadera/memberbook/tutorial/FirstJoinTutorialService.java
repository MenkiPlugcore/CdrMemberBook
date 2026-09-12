package id.cadera.memberbook.tutorial;

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
