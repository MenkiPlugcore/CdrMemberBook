package id.cadera.memberbook.util;

import org.bukkit.Sound;
import org.bukkit.entity.Player;
import id.cadera.memberbook.CdrMemberBookPlugin;

public final class Sounds {
    private Sounds() {}

    public static void play(CdrMemberBookPlugin plugin, Player player, String configPath) {
        String raw = plugin.getConfig().getString(configPath, "");
        if (raw == null || raw.isBlank()) return;
        try {
            Sound sound = Sound.valueOf(raw.toUpperCase());
            player.playSound(player.getLocation(), sound, 1.0f, 1.0f);
        } catch (IllegalArgumentException ignored) {
            plugin.getLogger().warning("Invalid sound in config: " + raw);
        }
    }
}
