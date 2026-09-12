from pathlib import Path

root = Path('.')

def read(path): return (root / path).read_text()
def write(path, content):
    p = root / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'pattern not found: {label}')
    return text.replace(old, new, 1)
def insert_before(text, marker, block, label):
    if marker not in text:
        raise SystemExit(f'marker not found: {label}')
    return text.replace(marker, block + marker, 1)

# Versions
p='pom.xml'; s=read(p); s=replace_once(s,'<version>1.11.0</version>','<version>1.11.0.1</version>','pom version'); write(p,s)
p='src/main/resources/plugin.yml'; s=read(p); s=replace_once(s,"version: '1.11.0'","version: '1.11.0.1'",'plugin version'); write(p,s)

# Config migration + runtime version
p='src/main/java/id/cadera/memberbook/CdrMemberBookPlugin.java'; s=read(p)
s=s.replace('getLogger().info("CdrMemberBook v1.11.0 enabled.");','getLogger().info("CdrMemberBook v1.11.0.1 enabled.");')
block='''        if (configVersion < 28) {\n            String material = getConfig().getString("member-book.material", "BOOK");\n            if (material == null || material.isBlank() || material.equalsIgnoreCase("BOOK")) {\n                getConfig().set("member-book.material", "WRITABLE_BOOK");\n            }\n            getConfig().set("member-book.interaction.hand-fallback", true);\n            getConfig().set("member-book.interaction.bedrock-open-delay-ticks", 1L);\n        }\n\n'''
s=insert_before(s,'        getConfig().set("config-version", 27);\n',block,'migration v28')
s=replace_once(s,'        getConfig().set("config-version", 27);\n','        getConfig().set("config-version", 28);\n','config version 28')
write(p,s)

# Bedrock-safe Member Book material + interaction fallback
p='src/main/java/id/cadera/memberbook/item/MemberBookService.java'; s=read(p)
s=replace_once(s,'import org.bukkit.inventory.ItemFlag;\n','import org.bukkit.inventory.ItemFlag;\nimport org.bukkit.inventory.EquipmentSlot;\n','equipment slot import')
s=replace_once(s,'String materialName = plugin.getConfig().getString("member-book.material", "BOOK");\n        Material material = materialName == null ? Material.BOOK : Material.matchMaterial(materialName);\n        if (material == null) material = Material.BOOK;','String materialName = plugin.getConfig().getString("member-book.material", "WRITABLE_BOOK");\n        Material material = materialName == null ? Material.WRITABLE_BOOK : Material.matchMaterial(materialName);\n        if (material == null) material = Material.WRITABLE_BOOK;','bedrock safe material fallback')
old='''        if (action != Action.RIGHT_CLICK_AIR && action != Action.RIGHT_CLICK_BLOCK) return;\n        if (!isMemberBook(event.getItem())) return;\n\n        event.setCancelled(true);\n        UUID uuid = player.getUniqueId();\n        long cooldownTicks = Math.max(0L, plugin.getConfig().getLong("member-book.open-cooldown-ticks", 20L));\n        if (cooldownTicks > 0L) {\n            if (!menuOpenCooldown.add(uuid)) return;\n            Bukkit.getScheduler().runTaskLater(plugin, () -> menuOpenCooldown.remove(uuid), cooldownTicks);\n        }\n        plugin.openMenu(player);\n'''
new='''        if (action != Action.RIGHT_CLICK_AIR && action != Action.RIGHT_CLICK_BLOCK) return;\n\n        ItemStack interacted = event.getItem();\n        if (!isMemberBook(interacted)\n                && plugin.getConfig().getBoolean("member-book.interaction.hand-fallback", true)) {\n            EquipmentSlot hand = event.getHand();\n            interacted = hand == EquipmentSlot.OFF_HAND\n                    ? player.getInventory().getItemInOffHand()\n                    : player.getInventory().getItemInMainHand();\n        }\n        if (!isMemberBook(interacted)) return;\n\n        event.setCancelled(true);\n        UUID uuid = player.getUniqueId();\n        long cooldownTicks = Math.max(0L, plugin.getConfig().getLong("member-book.open-cooldown-ticks", 20L));\n        if (cooldownTicks > 0L) {\n            if (!menuOpenCooldown.add(uuid)) return;\n            Bukkit.getScheduler().runTaskLater(plugin, () -> menuOpenCooldown.remove(uuid), cooldownTicks);\n        }\n\n        boolean bedrock = plugin.forms() != null && plugin.forms().isBedrock(player);\n        long openDelay = bedrock\n                ? Math.max(0L, plugin.getConfig().getLong("member-book.interaction.bedrock-open-delay-ticks", 1L))\n                : 0L;\n        if (openDelay > 0L) {\n            Bukkit.getScheduler().runTaskLater(plugin, () -> {\n                if (player.isOnline()) plugin.openMenu(player);\n            }, openDelay);\n        } else {\n            plugin.openMenu(player);\n        }\n'''
s=replace_once(s,old,new,'bedrock interaction handler')
write(p,s)

# Default config v28
p='src/main/resources/config.yml'; s=read(p)
s=replace_once(s,'# CdrMemberBook v1.11.0\nconfig-version: 27','# CdrMemberBook v1.11.0.1\nconfig-version: 28','config header')
s=replace_once(s,'  material: BOOK\n','  # WRITABLE_BOOK reliably produces a Bedrock/Geyser use-item interaction.\n  material: WRITABLE_BOOK\n','default writable book')
interaction='''  # Bedrock Interaction Hotfix v1.11.0.1\n  interaction:\n    # Jika Geyser mengirim PlayerInteractEvent tanpa event item, cek item di hand player.\n    hand-fallback: true\n    # Kirim Floodgate Form satu tick setelah use-item agar tidak bentrok dengan transaksi Bedrock.\n    bedrock-open-delay-ticks: 1\n\n'''
s=insert_before(s,'  # Safety & Recovery v1.4.0\n',interaction,'interaction config')
write(p,s)

# Admin health/version text
p='src/main/java/id/cadera/memberbook/command/MemberBookAdminCommand.java'; s=read(p)
s=s.replace('&dCdrMemberBook Health &8- &fv1.10.0','&dCdrMemberBook Health &8- &fv1.11.0.1')
s=s.replace('&dCdrMemberBook &fv1.10.0 &8- &7Admin Tools','&dCdrMemberBook &fv1.11.0.1 &8- &7Admin Tools')
write(p,s)

# Changelog
p='CHANGELOG.md'; s=read(p)
entry='''## 1.11.0.1 - Bedrock Interaction Hotfix\n\n- Changed the default Member Book material from `BOOK` to `WRITABLE_BOOK` for reliable Bedrock/Geyser use-item interaction.\n- Existing configs using the old default `BOOK` automatically migrate to `WRITABLE_BOOK`; custom materials are preserved.\n- Existing owned Member Books are refreshed to the configured material through the normal refresh/recovery lifecycle.\n- Added hand fallback detection when Geyser/Paper provides an empty interaction item.\n- Added a configurable 1-tick Bedrock form-open delay to avoid use-item transaction timing conflicts.\n- Java menu routing and existing Member Book safety/recovery behavior remain unchanged.\n- Config migrated to version 28.\n\n'''
s=replace_once(s,'# Changelog\n\n','# Changelog\n\n'+entry,'changelog header')
write(p,s)

# README version references where exact version appears
p='README.md'; s=read(p)
s=s.replace('CdrMemberBook-1.11.0.jar','CdrMemberBook-1.11.0.1.jar')
s=s.replace('v1.11.0','v1.11.0.1')
write(p,s)

print('v1.11.0.1 patch applied')
