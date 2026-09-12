package id.cadera.memberbook.tp;

import java.util.UUID;

public record TeleportRequest(
        UUID requesterId,
        UUID targetId,
        TeleportMode mode,
        long createdAtMillis
) {}
