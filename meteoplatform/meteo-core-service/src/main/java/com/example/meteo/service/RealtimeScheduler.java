package com.example.meteo.service;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class RealtimeScheduler {
  private final RealtimeIngestService ingest;

  public RealtimeScheduler(RealtimeIngestService ingest) {
    this.ingest = ingest;
  }

  @Scheduled(fixedRateString = "${meteo.polling.realtimeMs}")
  public void pollRealtime() {
    ingest.ingestRealtimeAndPublish();
  }
}
