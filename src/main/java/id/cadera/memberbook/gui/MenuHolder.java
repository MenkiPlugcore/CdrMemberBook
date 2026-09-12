package id.cadera.memberbook.gui;

import org.bukkit.Bukkit;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.event.inventory.InventoryType;
import org.jetbrains.annotations.NotNull;

import java.util.UUID;

public final class MenuHolder implements InventoryHolder {
    public enum Type {
        CONFIG,
        PLAYER_SELECT,
        TP_MODE,
        SETTINGS,
        SETTINGS_DEFAULT_MENU,
        REPORT_CENTER,
        REPORT_LIST,
        REPORT_DETAIL,
        REPORT_CONFIRM,
        REPORT_SEARCH_TYPE,
        REPORT_SEARCH_INPUT,
        REPORT_CATEGORY_FILTER,
        REPORT_CUSTOM_LIST,
        REPORT_NOTE_INPUT,
        REPORT_SUBMIT_CATEGORY,
        REPORT_SUBMIT_PLAYER,
        REPORT_SUBMIT_REASON,
        REPORT_SUBMIT_EVIDENCE,
        REPORT_SUBMIT_CONFIRM
    }

    private final Type type;
    private final UUID targetId;
    private final String menuId;
    private final int page;
    private final String context;
    private final int value;
    private final Inventory inventory;

    public MenuHolder(Type type, UUID targetId, String menuId, int page, int size, String title) {
        this(type, targetId, menuId, page, "", 0, size, title);
    }

    public MenuHolder(Type type, UUID targetId, String menuId, int page,
                      InventoryType inventoryType, String title) {
        this(type, targetId, menuId, page, "", 0, inventoryType, title);
    }

    public MenuHolder(Type type, UUID targetId, String menuId, int page, String context, int value,
                      InventoryType inventoryType, String title) {
        this.type = type;
        this.targetId = targetId;
        this.menuId = menuId == null ? "main" : menuId;
        this.page = Math.max(0, page);
        this.context = context == null ? "" : context;
        this.value = value;
        this.inventory = Bukkit.createInventory(this, inventoryType, title);
    }

    public MenuHolder(Type type, UUID targetId, String menuId, int page,
                      String context, int value, int size, String title) {
        this.type = type;
        this.targetId = targetId;
        this.menuId = menuId == null ? "main" : menuId;
        this.page = Math.max(0, page);
        this.context = context == null ? "" : context;
        this.value = value;
        this.inventory = Bukkit.createInventory(this, size, title);
    }

    public Type type() { return type; }
    public UUID targetId() { return targetId; }
    public String menuId() { return menuId; }
    public int page() { return page; }
    public String context() { return context; }
    public int value() { return value; }

    @Override
    public @NotNull Inventory getInventory() { return inventory; }
}
