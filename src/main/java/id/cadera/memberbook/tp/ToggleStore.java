package id.cadera.memberbook.tp;

import org.bukkit.configuration.file.YamlConfiguration;
import id.cadera.memberbook.CdrMemberBookPlugin;

import java.io.File;
import java.io.IOException;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

public final class ToggleStore {
    private final CdrMemberBookPlugin plugin;
    private final File file;
    private final YamlConfiguration yaml;
    private final Set<UUID> disabled = new HashSet<>();

    public ToggleStore(CdrMemberBookPlugin plugin) {
        this.plugin = plugin;
        this.file = new File(plugin.getDataFolder(), "data.yml");
        this.yaml = YamlConfiguration.loadConfiguration(file);
        for (String value : yaml.getStringList("teleport-disabled")) {
            try {
                disabled.add(UUID.fromString(value));
            } catch (IllegalArgumentException ignored) {
                plugin.getLogger().warning("Ignoring invalid UUID in data.yml: " + value);
            }
        }
    }

    public boolean isDisabled(UUID uuid) {
        return disabled.contains(uuid);
    }

    public boolean toggle(UUID uuid) {
        boolean nowDisabled;
        if (disabled.remove(uuid)) {
            nowDisabled = false;
        } else {
            disabled.add(uuid);
            nowDisabled = true;
        }
        save();
        return nowDisabled;
    }

    public void setDisabled(UUID uuid, boolean value) {
        if (value) disabled.add(uuid); else disabled.remove(uuid);
        save();
    }

    private void save() {
        yaml.set("teleport-disabled", disabled.stream().map(UUID::toString).sorted().toList());
        try {
            yaml.save(file);
        } catch (IOException e) {
            plugin.getLogger().severe("Could not save data.yml: " + e.getMessage());
        }
    }
}
