package id.cadera.memberbook.gui;

import org.bukkit.Bukkit;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.jetbrains.annotations.NotNull;

import java.util.UUID;

public final class MenuHolder implements InventoryHolder {
    public enum Type { CONFIG, PLAYER_SELECT, TP_MODE }

    private final Type type;
    private final UUID targetId;
    private final String menuId;
    private final int page;
    private final Inventory inventory;

    public MenuHolder(Type type, UUID targetId, String menuId, int page, int size, String title) {
        this.type = type;
        this.targetId = targetId;
        this.menuId = menuId == null ? "main" : menuId;
        this.page = Math.max(0, page);
        this.inventory = Bukkit.createInventory(this, size, title);
    }

    public Type type() {
        return type;
    }

    public UUID targetId() {
        return targetId;
    }

    public String menuId() {
        return menuId;
    }

    public int page() {
        return page;
    }

    @Override
    public @NotNull Inventory getInventory() {
        return inventory;
    }
}
