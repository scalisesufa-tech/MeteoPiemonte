package com.example.meteo.dto;

import java.time.Instant;

public record RealtimeEvent(
    String stationId,
    String stationName,
    String city,
    Double lat,
    Double lon,
    Instant observedAt,
    Double temperature,
    Double relativeHumidity,
    Double pressure
) {}
