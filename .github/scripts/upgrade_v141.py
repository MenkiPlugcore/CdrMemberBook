from pathlib import Path
import re

root = Path('.')

p = root / 'src/main/java/id/cadera/memberbook/item/MemberBookService.java'
s = p.read_text()

if 'import org.bukkit.inventory.ItemFlag;' not in s:
    s = s.replace('import org.bukkit.inventory.Inventory;\n', 'import org.bukkit.inventory.Inventory;\nimport org.bukkit.inventory.ItemFlag;\n')

old = """    public void giveToOnlinePlayers() {
        if (!isEnabled()) return;
        for (Player player : Bukkit.getOnlinePlayers()) {
            syncBookState(player, false);
        }
    }
"""
new = """    public void giveToOnlinePlayers() {
        if (!isEnabled()) return;
        for (Player player : Bukkit.getOnlinePlayers()) {
            if (isEligibleForBook(player) && refreshExistingEnabled()) {
                refreshVisibleBookAppearance(player);
            }
            syncBookState(player, false);
        }
    }

    public void refreshOnlineBooks() {
        if (!isEnabled() || !refreshExistingEnabled()) return;
        for (Player player : Bukkit.getOnlinePlayers()) {
            if (isEligibleForBook(player)) refreshVisibleBookAppearance(player);
        }
    }
"""
if old not in s:
    raise SystemExit('giveToOnlinePlayers pattern not found')
s = s.replace(old, new, 1)

old = """    public boolean forceGive(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        return reconcileMovableBook(player, true, true, true) && finishLockedMode(player);
    }

    public boolean forceRepair(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        boolean repaired = reconcileMovableBook(player, true, true, true);
        if (!repaired) return false;
        return finishLockedMode(player);
    }
"""
new = """    public boolean forceGive(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        if (refreshExistingEnabled()) refreshVisibleBookAppearance(player);
        return reconcileMovableBook(player, true, true, true) && finishLockedMode(player);
    }

    public boolean forceRepair(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        if (refreshExistingEnabled()) refreshVisibleBookAppearance(player);
        boolean repaired = reconcileMovableBook(player, true, true, true);
        if (!repaired) return false;
        return finishLockedMode(player);
    }
"""
if old not in s:
    raise SystemExit('forceGive/forceRepair pattern not found')
s = s.replace(old, new, 1)

create_pattern = re.compile(r"    private ItemStack createBook\(\) \{.*?^    \}\n\n    private boolean isEnabled\(\) \{", re.S | re.M)
replacement = """    private ItemStack createBook() {
        String materialName = plugin.getConfig().getString(\"member-book.material\", \"BOOK\");
        Material material = materialName == null ? Material.BOOK : Material.matchMaterial(materialName);
        if (material == null) material = Material.BOOK;

        ItemStack item = new ItemStack(material);
        applyConfiguredAppearance(item);
        return item;
    }

    private void applyConfiguredAppearance(ItemStack item) {
        ItemMeta meta = item.getItemMeta();
        if (meta == null) return;

        meta.setDisplayName(Colors.legacy(plugin.getConfig().getString(
                \"member-book.name\", \"&d&lMOONSIGN &fMember Book\")));

        List<String> lore = new ArrayList<>();
        for (String line : plugin.getConfig().getStringList(\"member-book.lore\")) {
            lore.add(Colors.legacy(line));
        }
        meta.setLore(lore.isEmpty() ? null : lore);

        String base = \"member-book.customization.\";

        int customModelData = plugin.getConfig().getInt(base + \"custom-model-data\", 0);
        if (customModelData > 0) meta.setCustomModelData(customModelData);

        String itemModelName = plugin.getConfig().getString(base + \"item-model\", \"\");
        if (itemModelName != null && !itemModelName.isBlank()) {
            NamespacedKey itemModel = NamespacedKey.fromString(itemModelName.trim());
            if (itemModel != null) meta.setItemModel(itemModel);
        }

        String glintMode = plugin.getConfig().getString(base + \"enchant-glint\", \"default\");
        if (glintMode != null) {
            switch (glintMode.trim().toLowerCase()) {
                case \"true\", \"on\", \"yes\", \"enabled\" -> meta.setEnchantmentGlintOverride(true);
                case \"false\", \"off\", \"no\", \"disabled\" -> meta.setEnchantmentGlintOverride(false);
                default -> meta.setEnchantmentGlintOverride(null);
            }
        }

        meta.setHideTooltip(plugin.getConfig().getBoolean(base + \"hide-tooltip\", false));
        if (plugin.getConfig().getBoolean(base + \"hide-attributes\", false)) {
            meta.addItemFlags(ItemFlag.HIDE_ATTRIBUTES);
        }
        if (plugin.getConfig().getBoolean(base + \"hide-additional-tooltip\", false)) {
            meta.addItemFlags(ItemFlag.HIDE_ADDITIONAL_TOOLTIP);
        }

        for (String configuredFlag : plugin.getConfig().getStringList(base + \"item-flags\")) {
            if (configuredFlag == null || configuredFlag.isBlank()) continue;
            try {
                meta.addItemFlags(ItemFlag.valueOf(configuredFlag.trim().toUpperCase()));
            } catch (IllegalArgumentException ignored) {
                // Invalid flags are ignored so a typo cannot prevent the plugin from starting.
            }
        }

        meta.getPersistentDataContainer().set(bookKey, PersistentDataType.BYTE, (byte) 1);
        item.setItemMeta(meta);
    }

    private void refreshVisibleBookAppearance(Player player) {
        PlayerInventory inventory = player.getInventory();
        for (int slot = 0; slot < inventory.getSize(); slot++) {
            ItemStack current = inventory.getItem(slot);
            if (isMemberBook(current)) inventory.setItem(slot, refreshedBook());
        }

        ItemStack cursor = player.getItemOnCursor();
        if (isMemberBook(cursor)) player.setItemOnCursor(refreshedBook());

        if (isExternalView(player)) {
            Inventory top = player.getOpenInventory().getTopInventory();
            for (int slot = 0; slot < top.getSize(); slot++) {
                ItemStack current = top.getItem(slot);
                if (isMemberBook(current)) top.setItem(slot, refreshedBook());
            }
        }
    }

    private ItemStack refreshedBook() {
        ItemStack refreshed = createBook();
        refreshed.setAmount(1);
        return refreshed;
    }

    private boolean refreshExistingEnabled() {
        return plugin.getConfig().getBoolean(\"member-book.customization.refresh-existing\", true);
    }

    private boolean isEnabled() {"""
s, n = create_pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'createBook replacement count={n}')

old = """        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (player.isOnline()) syncBookState(player, true);
        }, delay);
"""
new = """        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (!player.isOnline()) return;
            if (isEligibleForBook(player) && refreshExistingEnabled()) refreshVisibleBookAppearance(player);
            syncBookState(player, true);
        }, delay);
"""
if old not in s:
    raise SystemExit('join delayed sync pattern not found')
s = s.replace(old, new, 1)
p.write_text(s)

p = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = p.read_text()
s = s.replace('CdrMemberBook v1.4.0 enabled.', 'CdrMemberBook v1.4.1 enabled.')
old = """        if (configVersion < 5) {
            getConfig().set(\"member-book.recovery.enabled\", true);
            getConfig().set(\"member-book.recovery.interval-ticks\", 100L);
            getConfig().set(\"member-book.recovery.recover-on-world-change\", true);
            getConfig().set(\"member-book.recovery.recover-from-open-container\", true);
            getConfig().set(\"member-book.recovery.remove-duplicates\", true);
        }

        getConfig().set(\"config-version\", 5);
"""
new = """        if (configVersion < 5) {
            getConfig().set(\"member-book.recovery.enabled\", true);
            getConfig().set(\"member-book.recovery.interval-ticks\", 100L);
            getConfig().set(\"member-book.recovery.recover-on-world-change\", true);
            getConfig().set(\"member-book.recovery.recover-from-open-container\", true);
            getConfig().set(\"member-book.recovery.remove-duplicates\", true);
        }

        if (configVersion < 6) {
            getConfig().set(\"member-book.customization.custom-model-data\", 0);
            getConfig().set(\"member-book.customization.item-model\", \"\");
            getConfig().set(\"member-book.customization.enchant-glint\", \"default\");
            getConfig().set(\"member-book.customization.hide-tooltip\", false);
            getConfig().set(\"member-book.customization.hide-attributes\", false);
            getConfig().set(\"member-book.customization.hide-additional-tooltip\", false);
            getConfig().set(\"member-book.customization.item-flags\", java.util.List.of());
            getConfig().set(\"member-book.customization.refresh-existing\", true);
        }

        getConfig().set(\"config-version\", 6);
"""
if old not in s:
    raise SystemExit('config migration pattern not found')
s = s.replace(old, new, 1)
p.write_text(s)

p = root / 'pom.xml'
s = p.read_text().replace('<version>1.4.0</version>', '<version>1.4.1</version>', 1)
p.write_text(s)

p = root / 'src/main/resources/plugin.yml'
s = p.read_text().replace("version: '1.4.0'", "version: '1.4.1'", 1)
p.write_text(s)

p = root / 'src/main/resources/config.yml'
s = p.read_text()
s = s.replace('# CdrMemberBook v1.4.0', '# CdrMemberBook v1.4.1', 1)
s = s.replace('config-version: 5', 'config-version: 6', 1)
s = s.replace('# Default v1.4.0:', '# Default v1.4.1:', 1)
s = s.replace('# Legacy compatibility option. Mode default v1.4.0 tidak mengunci perpindahan internal.', '# Legacy compatibility option. Mode default v1.4.1 tidak mengunci perpindahan internal.', 1)
marker = """  lore:
  - '&7Klik kanan untuk membuka Menu Member.'
  - '&8Item menu pribadi MOONSIGN.'
"""
block = """  lore:
  - '&7Klik kanan untuk membuka Menu Member.'
  - '&8Item menu pribadi MOONSIGN.'

  # Book Customization v1.4.1
  customization:
    # 0 = nonaktif. Cocok untuk resource pack Java / legacy Geyser custom item mapping.
    custom-model-data: 0
    # Format namespace:key, contoh: moonsign:member_book. Kosong = model vanilla.
    # Untuk Bedrock, model custom tetap membutuhkan Geyser custom mapping + Bedrock resource pack.
    item-model: ''
    # true = paksa glint, false = paksa tanpa glint, default = perilaku vanilla.
    enchant-glint: default
    # Menyembunyikan seluruh tooltip item. Jika true, nama/lore juga tidak terlihat di tooltip.
    hide-tooltip: false
    hide-attributes: false
    hide-additional-tooltip: false
    # ItemFlag Bukkit tambahan, contoh: [HIDE_ENCHANTS, HIDE_UNBREAKABLE]
    item-flags: []
    # Buku lama milik player online otomatis mengikuti tampilan config terbaru saat reload/join.
    refresh-existing: true
"""
if marker not in s:
    raise SystemExit('config lore marker not found')
s = s.replace(marker, block, 1)
p.write_text(s)

p = root / 'CHANGELOG.md'
s = p.read_text()
insert_at = s.index('## 1.4.0 — Member Book Safety & Recovery')
entry = """## 1.4.1 — Book Customization

- Added configurable `custom-model-data` for legacy/custom resource-pack item models.
- Added Minecraft 1.21.4+ `item-model` support using namespaced item model keys such as `moonsign:member_book`.
- Added tri-state `enchant-glint`: `true`, `false`, or `default`.
- Added optional `hide-tooltip`, `hide-attributes`, and `hide-additional-tooltip` controls.
- Added arbitrary Bukkit `item-flags` list support for advanced item presentation.
- Existing `material`, `name`, and `lore` settings remain fully configurable and backward compatible.
- Added `refresh-existing`; online Bedrock players' existing Member Books can be restyled automatically on join/reload without deleting and re-giving the book.
- `/cdrmemberbook give` and `/cdrmemberbook fix` now refresh the appearance of an existing book before recovery/repair.
- Customization never removes the Member Book PDC identity marker, so Safety & Recovery protections continue to work after restyling.
- Config migration v5 -> v6 automatically adds customization defaults without changing the current visual appearance.
- Version bumped to `1.4.1`.

"""
s = s[:insert_at] + entry + s[insert_at:]
p.write_text(s)

p = root / 'README.md'
s = p.read_text()
s = s.replace('# CdrMemberBook v1.4.0', '# CdrMemberBook v1.4.1', 1)
s = s.replace('target/CdrMemberBook-1.4.0.jar', 'target/CdrMemberBook-1.4.1.jar')
anchor = '## Member Book Safety & Recovery\n'
if anchor in s and '## Book Customization' not in s:
    section = """## Book Customization

`v1.4.1` menambahkan kontrol tampilan item tanpa mengubah identitas/proteksi Member Book.

```yaml
member-book:
  material: BOOK
  name: '&d&lMOONSIGN &fMember Book'
  lore:
    - '&7Klik kanan untuk membuka Menu Member.'
  customization:
    custom-model-data: 0
    item-model: ''
    enchant-glint: default
    hide-tooltip: false
    hide-attributes: false
    hide-additional-tooltip: false
    item-flags: []
    refresh-existing: true
```

`item-model` memakai format `namespace:key` dan ditujukan untuk sistem item model Minecraft 1.21.4+. `custom-model-data` tetap tersedia untuk kompatibilitas legacy. Untuk client Bedrock melalui Geyser, model/tekstur custom memerlukan Geyser custom item mapping dan Bedrock resource pack; plugin hanya menetapkan komponen item Java yang menjadi basis mapping.

`/menu reload` akan menerapkan konfigurasi tampilan terbaru ke Member Book player online jika `refresh-existing: true`.

"""
    s = s.replace(anchor, section + anchor, 1)
p.write_text(s)
