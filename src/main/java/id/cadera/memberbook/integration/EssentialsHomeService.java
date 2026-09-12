package id.cadera.memberbook.integration;

import com.earth2me.essentials.Essentials;
import com.earth2me.essentials.User;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.plugin.Plugin;
import id.cadera.memberbook.CdrMemberBookPlugin;

import java.util.List;

public final class EssentialsHomeService {
    private final CdrMemberBookPlugin plugin;
    private Essentials essentials;

    public EssentialsHomeService(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
    }

    public boolean initialize() {
        Plugin candidate = Bukkit.getPluginManager().getPlugin("Essentials");
        if (!(candidate instanceof Essentials found) || !candidate.isEnabled()) {
            essentials = null;
            return false;
        }
        essentials = found;
        return true;
    }

    public boolean available() {
        return essentials != null && essentials.isEnabled();
    }

    public List<String> homes(Player player) {
        User user = user(player);
        return user == null ? List.of() : List.copyOf(user.getHomes());
    }

    /**
     * @return -1 when unlimited, otherwise the effective EssentialsX home limit.
     */
    public int maxHomes(Player player) {
        if (player.hasPermission("essentials.sethome.multiple.unlimited")) return -1;
        User user = user(player);
        if (user == null) return 0;
        return essentials.getSettings().getHomeLimit(user);
    }

    private User user(Player player) {
        if (!available()) return null;
        try {
            return essentials.getUser(player.getUniqueId());
        } catch (Throwable throwable) {
            plugin.getLogger().warning("Failed to read EssentialsX user " + player.getName() + ": " + throwable.getMessage());
            return null;
        }
    }
}
