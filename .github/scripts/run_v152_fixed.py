from pathlib import Path

script = Path('.github/scripts/upgrade_v152.py')
source = script.read_text()
source = source.replace(
    'Gunakan `type: homes`. CdrMemberBook membaca data home dan limit langsung dari EssentialsX, lalu menyediakan daftar home, set home baru, teleport, hapus dengan konfirmasi, serta dukungan home unlimited.',
    'Gunakan `type: homes`. Mulai v1.5.1, Home Manager Bedrock memakai flow klik penuh: **Teleport Home**, **Set Home**, **Hapus Home**, lalu picker nama home. Player tidak perlu mengetik `/home` atau `/sethome`.'
)
exec(compile(source, str(script), 'exec'))
