from pathlib import Path
import re

root = Path('.')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)

def regex_once(text, pattern, repl, label):
    out, n = re.subn(pattern, repl, text, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f'regex pattern not found/ambiguous ({n}): {label}')
    return out

# -----------------------------------------------------------------------------
# MemberBookService.java — Book Modes v1.6.0
# -----------------------------------------------------------------------------
p = root / 'src/main/java/id/cadera/memberbook/item/MemberBookService.java'
s = p.read_text()

s = replace_once(
    s,
    '    private final Set<UUID> menuOpenCooldown = new HashSet<>();\n',
    '    private final Set<UUID> menuOpenCooldown = new HashSet<>();\n'
    '    private final Set<UUID> fixedSlotReturnPending = new HashSet<>();\n',
    'fixed slot pending field'
)

s = regex_once(
    s,
    r'    public void startEnforcement\(\) \{.*?\n    \}\n\n    private void startDynamicRefresh\(\)',
    '''    public void startEnforcement() {
        stopEnforcement();
        if (!isEnabled()) return;

        BookMode mode = bookMode();
        boolean needsEnforcement = mode == BookMode.LOCKED_HOTBAR
                || mode == BookMode.FIXED_SLOT_MOVABLE
                || (mode == BookMode.MOVABLE && recoveryEnabled());

        if (needsEnforcement) {
            long configuredPeriod = switch (mode) {
                case LOCKED_HOTBAR -> plugin.getConfig().getLong("member-book.enforce-interval-ticks", 20L);
                case FIXED_SLOT_MOVABLE -> plugin.getConfig().getLong(
                        "member-book.fixed-slot.return-delay-ticks", 40L);
                default -> plugin.getConfig().getLong("member-book.recovery.interval-ticks", 100L);
            };
            long period = Math.max(20L, configuredPeriod);

            enforcementTask = Bukkit.getScheduler().runTaskTimer(plugin, () -> {
                for (Player player : Bukkit.getOnlinePlayers()) {
                    syncBookState(player, false);
                }
            }, period, period);
        }

        startDynamicRefresh();
    }

    private void startDynamicRefresh()''',
    'start enforcement'
)

s = regex_once(
    s,
    r'    public boolean forceGive\(Player player\) \{.*?\n    \}\n\n    public boolean forceRepair\(Player player\) \{.*?\n    \}',
    '''    public boolean forceGive(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        if (refreshExistingEnabled()) refreshVisibleBookAppearance(player);
        boolean given = reconcileMovableBook(player, true, true, true);
        return given && finishBookMode(player);
    }

    public boolean forceRepair(Player player) {
        if (!isEligibleForBook(player)) return false;
        recoverySuppressed.remove(player.getUniqueId());
        if (refreshExistingEnabled()) refreshVisibleBookAppearance(player);
        boolean repaired = reconcileMovableBook(player, true, true, true);
        if (!repaired) return false;
        return finishBookMode(player);
    }''',
    'force give repair'
)

s = regex_once(
    s,
    r'    private boolean finishLockedMode\(Player player\) \{.*?\n    \}',
    '''    private boolean finishBookMode(Player player) {
        BookMode mode = bookMode();
        if (mode != BookMode.LOCKED_HOTBAR && mode != BookMode.FIXED_SLOT_MOVABLE) {
            return hasOwnedBook(player);
        }
        if (isMemberBook(player.getItemOnCursor())) return true;
        ensureLockedHotbarBook(player);
        return hasOwnedBook(player);
    }''',
    'finish book mode'
)

s = regex_once(
    s,
    r'    private void syncBookState\(Player player, boolean notifyFull\) \{.*?\n    \}\n\n    private boolean reconcileMovableBook',
    '''    private void syncBookState(Player player, boolean notifyFull) {
        if (!isEnabled()) return;

        if (!isEligibleForBook(player)) {
            if (isBedrockOnly()) removeAllVisibleBooks(player, false);
            return;
        }

        if (recoverySuppressed.contains(player.getUniqueId())) return;

        BookMode mode = bookMode();
        if (mode == BookMode.NORMAL) {
            // NORMAL behaves like a regular item: no periodic recovery, slot enforcement,
            // duplicate cleanup, drop protection or external-storage protection.
            if (notifyFull && giveOnJoinEnabled() && !hasOwnedBook(player)) {
                if (!placeBookInPlayer(player, createBook(player))) {
                    plugin.message(player, "member-book-inventory-full");
                }
            }
            return;
        }

        if (mode == BookMode.LOCKED_HOTBAR || mode == BookMode.FIXED_SLOT_MOVABLE) {
            reconcileMovableBook(player, false, false, false);
            if (isMemberBook(player.getItemOnCursor())) return;
            ensureLockedHotbarBook(player);
            return;
        }

        reconcileMovableBook(player, shouldMaintain(), notifyFull, false);
    }

    private boolean reconcileMovableBook''',
    'sync book state'
)

old_helpers = '''    private boolean shouldMaintain() {
        return isPermanentHotbar() || plugin.getConfig().getBoolean("member-book.give-on-join", true);
    }

    private boolean isPermanentHotbar() {
        return plugin.getConfig().getBoolean("member-book.permanent-hotbar", false);
    }

    private boolean preventExternalStorage() {
        return plugin.getConfig().getBoolean("member-book.prevent-external-storage", true);
    }

    private boolean recoveryEnabled() {
        return plugin.getConfig().getBoolean("member-book.recovery.enabled", true);
    }

    private boolean recoverFromOpenContainer() {
        return plugin.getConfig().getBoolean("member-book.recovery.recover-from-open-container", true);
    }

    private boolean removeDuplicatesEnabled() {
        return plugin.getConfig().getBoolean("member-book.recovery.remove-duplicates", true);
    }

    private boolean recoverOnWorldChange() {
        return plugin.getConfig().getBoolean("member-book.recovery.recover-on-world-change", true);
    }
'''
new_helpers = '''    private boolean shouldMaintain() {
        return bookMode() != BookMode.NORMAL && giveOnJoinEnabled();
    }

    private boolean giveOnJoinEnabled() {
        return plugin.getConfig().getBoolean("member-book.give-on-join", true);
    }

    private BookMode bookMode() {
        String configured = plugin.getConfig().getString("member-book.mode", "");
        if (configured == null || configured.isBlank()) {
            return plugin.getConfig().getBoolean("member-book.permanent-hotbar", false)
                    ? BookMode.LOCKED_HOTBAR
                    : BookMode.MOVABLE;
        }
        try {
            return BookMode.valueOf(configured.trim().toUpperCase());
        } catch (IllegalArgumentException ignored) {
            return BookMode.MOVABLE;
        }
    }

    public String modeName() {
        return bookMode().name();
    }

    private boolean isPermanentHotbar() {
        return bookMode() == BookMode.LOCKED_HOTBAR;
    }

    private boolean preventExternalStorage() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.prevent-external-storage", true);
    }

    private boolean recoveryEnabled() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.recovery.enabled", true);
    }

    private boolean recoverFromOpenContainer() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.recovery.recover-from-open-container", true);
    }

    private boolean removeDuplicatesEnabled() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.recovery.remove-duplicates", true);
    }

    private boolean recoverOnWorldChange() {
        return bookMode() != BookMode.NORMAL
                && plugin.getConfig().getBoolean("member-book.recovery.recover-on-world-change", true);
    }
'''
s = replace_once(s, old_helpers, new_helpers, 'mode helpers')

old_schedule = '''    private void scheduleRepair(Player player) {
        Bukkit.getScheduler().runTask(plugin, () -> {
            if (player.isOnline()) syncBookState(player, false);
        });
    }
'''
new_schedule = '''    private void scheduleRepair(Player player) {
        if (bookMode() == BookMode.NORMAL) return;
        if (bookMode() == BookMode.FIXED_SLOT_MOVABLE) {
            UUID uuid = player.getUniqueId();
            if (!fixedSlotReturnPending.add(uuid)) return;
            long delay = Math.max(1L, plugin.getConfig().getLong(
                    "member-book.fixed-slot.return-delay-ticks", 40L));
            Bukkit.getScheduler().runTaskLater(plugin, () -> {
                fixedSlotReturnPending.remove(uuid);
                if (player.isOnline()) syncBookState(player, false);
            }, delay);
            return;
        }
        Bukkit.getScheduler().runTask(plugin, () -> {
            if (player.isOnline()) syncBookState(player, false);
        });
    }
'''
s = replace_once(s, old_schedule, new_schedule, 'schedule repair')

# NORMAL must not recreate a book after death/respawn.
s = replace_once(
    s,
    '            if (player.isOnline()) syncBookState(player, true);\n        }, 1L);\n    }\n\n    @EventHandler\n    public void onWorldChange',
    '            if (player.isOnline()) syncBookState(player, bookMode() != BookMode.NORMAL);\n        }, 1L);\n    }\n\n    @EventHandler\n    public void onWorldChange',
    'normal respawn no recovery'
)

# LOCKED_HOTBAR prevents internal movement, while FIXED_SLOT_MOVABLE allows it and returns later.
needle = '''        boolean clickedForeignInventory = event.getClickedInventory() != null && !clickedOwnInventory;
        boolean touchedBook = cursorBook || currentBook;

        if (cursorBook && clickedForeignInventory) {
'''
replacement = '''        boolean clickedForeignInventory = event.getClickedInventory() != null && !clickedOwnInventory;
        boolean touchedBook = cursorBook || currentBook;

        if (bookMode() == BookMode.LOCKED_HOTBAR) {
            int hotbarButton = event.getHotbarButton();
            boolean reservedHotbarSwap = hotbarButton == reservedSlot()
                    && isMemberBook(player.getInventory().getItem(reservedSlot()));
            if (touchedBook || reservedHotbarSwap) {
                event.setCancelled(true);
                scheduleRepair(player);
                return;
            }
        }

        if (cursorBook && clickedForeignInventory) {
'''
s = replace_once(s, needle, replacement, 'locked click movement')

# Avoid duplicate local variable after locked-mode insertion.
s = replace_once(s, '        int hotbarButton = event.getHotbarButton();\n        if (clickedForeignInventory && hotbarButton >= 0',
                 '        int hotbarButton = event.getHotbarButton();\n        if (clickedForeignInventory && hotbarButton >= 0', 'hotbar variable check')
# Rename the inserted scoped variable to avoid Java scope collision with later hotbarButton.
s = s.replace('            int hotbarButton = event.getHotbarButton();\n            boolean reservedHotbarSwap = hotbarButton == reservedSlot()',
              '            int lockedHotbarButton = event.getHotbarButton();\n            boolean reservedHotbarSwap = lockedHotbarButton == reservedSlot()', 1)

# Dragging a locked book is always blocked. Movable/fixed retain external-storage checks.
s = replace_once(
    s,
    '''        if (!isEligibleForBook(player) || !preventExternalStorage()) return;
        if (!isMemberBook(event.getOldCursor())) return;

        int topSize = event.getView().getTopInventory().getSize();
''',
    '''        if (!isEligibleForBook(player)) return;
        if (!isMemberBook(event.getOldCursor())) return;
        if (bookMode() == BookMode.LOCKED_HOTBAR) {
            event.setCancelled(true);
            scheduleRepair(player);
            return;
        }
        if (!preventExternalStorage()) return;

        int topSize = event.getView().getTopInventory().getSize();
''',
    'locked drag movement'
)

s = replace_once(s,
'''    public void onInventoryMove(InventoryMoveItemEvent event) {
        if (isMemberBook(event.getItem())) event.setCancelled(true);
    }
''',
'''    public void onInventoryMove(InventoryMoveItemEvent event) {
        if (bookMode() != BookMode.NORMAL && isMemberBook(event.getItem())) event.setCancelled(true);
    }
''', 'normal hopper move')

s = replace_once(s,
'''    public void onInventoryPickup(InventoryPickupItemEvent event) {
        if (isMemberBook(event.getItem().getItemStack())) event.setCancelled(true);
    }
''',
'''    public void onInventoryPickup(InventoryPickupItemEvent event) {
        if (bookMode() != BookMode.NORMAL && isMemberBook(event.getItem().getItemStack())) event.setCancelled(true);
    }
''', 'normal hopper pickup')

s = replace_once(s,
'''    public void onDispense(BlockDispenseEvent event) {
        if (isMemberBook(event.getItem())) event.setCancelled(true);
    }
''',
'''    public void onDispense(BlockDispenseEvent event) {
        if (bookMode() != BookMode.NORMAL && isMemberBook(event.getItem())) event.setCancelled(true);
    }
''', 'normal dispense')

s = replace_once(s,
'''        Item itemEntity = event.getItem();
        if (!isMemberBook(itemEntity.getItemStack())) return;

        event.setCancelled(true);
''',
'''        Item itemEntity = event.getItem();
        if (!isMemberBook(itemEntity.getItemStack())) return;
        if (bookMode() == BookMode.NORMAL) return;

        event.setCancelled(true);
''', 'normal entity pickup')

s = replace_once(s,
'''    public void onDrop(PlayerDropItemEvent event) {
        if (!isEligibleForBook(event.getPlayer())) return;
        if (!plugin.getConfig().getBoolean("member-book.prevent-drop", true)) return;
''',
'''    public void onDrop(PlayerDropItemEvent event) {
        if (!isEligibleForBook(event.getPlayer())) return;
        if (bookMode() == BookMode.NORMAL) return;
        if (!plugin.getConfig().getBoolean("member-book.prevent-drop", true)) return;
''', 'normal drop')

s = replace_once(s,
'''    public void onDeath(PlayerDeathEvent event) {
        if (!isEnabled()) return;
        event.getDrops().removeIf(this::isMemberBook);
    }
''',
'''    public void onDeath(PlayerDeathEvent event) {
        if (!isEnabled() || bookMode() == BookMode.NORMAL) return;
        event.getDrops().removeIf(this::isMemberBook);
    }
''', 'normal death')

s = replace_once(s,
'''        Player player = event.getPlayer();
        menuOpenCooldown.remove(player.getUniqueId());
        if (!isMemberBook(player.getItemOnCursor())) return;
''',
'''        Player player = event.getPlayer();
        menuOpenCooldown.remove(player.getUniqueId());
        fixedSlotReturnPending.remove(player.getUniqueId());
        if (bookMode() == BookMode.NORMAL) return;
        if (!isMemberBook(player.getItemOnCursor())) return;
''', 'normal quit and pending cleanup')

# Add enum before final class brace.
s = replace_once(s,
'''    private boolean hasInventoryBook(Player player) {
        for (ItemStack item : player.getInventory().getContents()) {
            if (isMemberBook(item)) return true;
        }
        return false;
    }
}
''',
'''    private boolean hasInventoryBook(Player player) {
        for (ItemStack item : player.getInventory().getContents()) {
            if (isMemberBook(item)) return true;
        }
        return false;
    }

    private enum BookMode {
        MOVABLE,
        LOCKED_HOTBAR,
        FIXED_SLOT_MOVABLE,
        NORMAL
    }
}
''', 'book mode enum')

p.write_text(s)

# -----------------------------------------------------------------------------
# Main plugin — migration v10 -> v11 and startup version/mode log
# -----------------------------------------------------------------------------
p = root / 'src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'
s = p.read_text()
s = replace_once(s, 'CdrMemberBook v1.5.3 enabled.', 'CdrMemberBook v1.6.0 enabled.', 'enable version')
s = replace_once(s,
'''        if (configVersion < 10) {
            getConfig().set("integrations.essentials-home.hide-locked-presets", true);
            getConfig().set("integrations.essentials-home.use-display-names-on-owned-homes", true);
            setPresetDefaults("rumah", "Rumah", "textures/items/bed_red");
            setPresetDefaults("base", "Base", "textures/items/bed_red");
            setPresetDefaults("farm", "Farm", "textures/items/wheat");
            setPresetDefaults("tambang", "Tambang", "textures/items/iron_pickaxe");
            setPresetDefaults("shop", "Shop", "textures/items/emerald");
        }

        getConfig().set("config-version", 10);
''',
'''        if (configVersion < 10) {
            getConfig().set("integrations.essentials-home.hide-locked-presets", true);
            getConfig().set("integrations.essentials-home.use-display-names-on-owned-homes", true);
            setPresetDefaults("rumah", "Rumah", "textures/items/bed_red");
            setPresetDefaults("base", "Base", "textures/items/bed_red");
            setPresetDefaults("farm", "Farm", "textures/items/wheat");
            setPresetDefaults("tambang", "Tambang", "textures/items/iron_pickaxe");
            setPresetDefaults("shop", "Shop", "textures/items/emerald");
        }

        if (configVersion < 11) {
            if (!getConfig().isSet("member-book.mode")) {
                getConfig().set("member-book.mode",
                        getConfig().getBoolean("member-book.permanent-hotbar", false)
                                ? "LOCKED_HOTBAR" : "MOVABLE");
            }
            getConfig().set("member-book.fixed-slot.return-delay-ticks", 40L);
        }

        getConfig().set("config-version", 11);
''', 'config v11 migration')
s = replace_once(s,
'''        memberBookService.giveToOnlinePlayers();
        memberBookService.startEnforcement();
        getLogger().info("CdrMemberBook v1.6.0 enabled.");
''',
'''        memberBookService.giveToOnlinePlayers();
        memberBookService.startEnforcement();
        getLogger().info("Member Book mode: " + memberBookService.modeName());
        getLogger().info("CdrMemberBook v1.6.0 enabled.");
''', 'startup mode log')
p.write_text(s)

# -----------------------------------------------------------------------------
# Versions
# -----------------------------------------------------------------------------
p = root / 'pom.xml'
s = p.read_text()
s = replace_once(s, '<version>1.5.3</version>', '<version>1.6.0</version>', 'pom version')
p.write_text(s)

p = root / 'src/main/resources/plugin.yml'
s = p.read_text()
s = replace_once(s, "version: '1.5.3'", "version: '1.6.0'", 'plugin version')
p.write_text(s)

# -----------------------------------------------------------------------------
# config.yml
# -----------------------------------------------------------------------------
p = root / 'src/main/resources/config.yml'
s = p.read_text()
s = replace_once(s, '# CdrMemberBook v1.5.3', '# CdrMemberBook v1.6.0', 'config header')
s = replace_once(s, 'config-version: 10', 'config-version: 11', 'config version')
s = s.replace('# Default v1.5.3:', '# Default v1.6.0:', 1)
s = s.replace('# Legacy compatibility option. Mode default v1.5.3 tidak mengunci perpindahan internal.',
              '# Legacy compatibility option. `mode` v1.6.0 menjadi sumber utama behavior buku.', 1)
s = replace_once(s,
'''  give-on-join: true
  give-delay-ticks: 10
  permanent-hotbar: false
''',
'''  give-on-join: true
  give-delay-ticks: 10

  # Book Modes v1.6.0:
  # MOVABLE            = bebas di inventory sendiri + Safety/Recovery aktif.
  # LOCKED_HOTBAR      = dikunci dan dijaga tetap di hotbar-slot.
  # FIXED_SLOT_MOVABLE = boleh dipindah sementara, lalu otomatis kembali ke hotbar-slot.
  # NORMAL             = item biasa; tanpa recovery, anti-drop, anti-storage, atau slot enforcement.
  mode: MOVABLE

  # Legacy compatibility. Config lama dengan permanent-hotbar: true otomatis
  # dimigrasikan ke mode LOCKED_HOTBAR saat naik ke config-version 11.
  permanent-hotbar: false
''', 'book mode config block')
s = replace_once(s,
'''  # Dipakai oleh mode legacy permanent-hotbar.
  enforce-interval-ticks: 20
  # Slot awal saat buku pertama kali diberikan jika slot ini kosong.
  hotbar-slot: 8
''',
'''  # Interval enforcement LOCKED_HOTBAR.
  enforce-interval-ticks: 20
  # Slot target 0-8 untuk LOCKED_HOTBAR/FIXED_SLOT_MOVABLE,
  # dan slot awal pemberian untuk MOVABLE/NORMAL jika kosong.
  hotbar-slot: 8
  fixed-slot:
    # FIXED_SLOT_MOVABLE mengembalikan buku ke hotbar-slot setelah delay ini.
    # 40 ticks = 2 detik.
    return-delay-ticks: 40
''', 'fixed slot config')
p.write_text(s)

# -----------------------------------------------------------------------------
# CHANGELOG
# -----------------------------------------------------------------------------
p = root / 'CHANGELOG.md'
s = p.read_text()
marker = '## 1.5.3 — Home Manager Advanced\n'
entry = '''## 1.6.0 — Book Modes

- Added `member-book.mode` with four modes: `MOVABLE`, `LOCKED_HOTBAR`, `FIXED_SLOT_MOVABLE`, and `NORMAL`.
- `MOVABLE` preserves the current production behavior: free movement inside the player's own inventory while Safety & Recovery and external-storage protection remain active.
- `LOCKED_HOTBAR` keeps one Member Book in `hotbar-slot`, blocks direct movement of the book, and continuously restores the configured slot.
- `FIXED_SLOT_MOVABLE` allows temporary internal movement but returns the Member Book to `hotbar-slot` after `fixed-slot.return-delay-ticks` (40 ticks by default).
- `NORMAL` behaves like a regular item: no periodic recovery, no duplicate cleanup, no anti-drop, no external-storage protection, no hopper/dispenser protection, and no death-drop removal. Right-click still opens the menu.
- `NORMAL` can still honor `give-on-join`; because the plugin intentionally does not search arbitrary containers in this mode, servers that want a fully manual normal item should set `give-on-join: false` and use the admin give command.
- Legacy `permanent-hotbar: true` automatically migrates to `LOCKED_HOTBAR`; other existing installations migrate to `MOVABLE` so current production behavior is preserved.
- Added mode name logging on plugin startup and safe fallback to `MOVABLE` for an invalid mode value.
- Config migration v10 -> v11 adds mode and fixed-slot defaults.
- Version bumped to `1.6.0`.

'''
if marker not in s:
    raise SystemExit('changelog marker missing')
s = s.replace(marker, entry + marker, 1)
p.write_text(s)

# -----------------------------------------------------------------------------
# README
# -----------------------------------------------------------------------------
p = root / 'README.md'
s = p.read_text()
s = replace_once(s, '# CdrMemberBook v1.5.3', '# CdrMemberBook v1.6.0', 'readme title')
insert_at = '## Dynamic Member Book\n'
book_modes = '''## Book Modes v1.6.0

Behavior Member Book sekarang dapat dipilih melalui `member-book.mode` tanpa compile ulang:

```yaml
member-book:
  mode: MOVABLE
  hotbar-slot: 8
  enforce-interval-ticks: 20
  fixed-slot:
    return-delay-ticks: 40
```

| Mode | Behavior |
|---|---|
| `MOVABLE` | Default production. Buku bebas dipindah di inventory sendiri; anti-drop, external-storage protection, dan Safety & Recovery tetap aktif. |
| `LOCKED_HOTBAR` | Buku dijaga di `hotbar-slot` dan perpindahan langsung diblok. Cocok untuk server yang ingin tombol menu permanen. |
| `FIXED_SLOT_MOVABLE` | Player boleh memindahkan buku, tetapi setelah delay buku otomatis dikembalikan ke `hotbar-slot`. |
| `NORMAL` | Member Book menjadi item biasa. Bisa dibuang/disimpan/dipindah normal; tidak ada recovery atau slot enforcement. Right-click tetap membuka menu. |

`NORMAL` tetap dapat memakai `give-on-join: true`, tetapi plugin sengaja tidak melacak buku di chest/container pada mode ini. Untuk item normal yang sepenuhnya manual gunakan `give-on-join: false`, lalu berikan melalui `/cdrmemberbook give <player>`.

Config lama tetap aman: `permanent-hotbar: true` dimigrasikan menjadi `LOCKED_HOTBAR`, sedangkan instalasi lainnya menjadi `MOVABLE`.

'''
if insert_at not in s:
    raise SystemExit('readme insertion marker missing')
s = s.replace(insert_at, book_modes + insert_at, 1)
s = s.replace('target/CdrMemberBook-1.5.3.jar', 'target/CdrMemberBook-1.6.0.jar')
p.write_text(s)

print('v1.6.0 Book Modes patch applied')
