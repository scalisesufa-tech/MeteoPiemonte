package com.example.meteo.controller;

import com.example.meteo.model.MeteoObservation;
import com.example.meteo.repository.MeteoObservationRepository;
import com.example.meteo.service.RealtimeIngestService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.data.domain.PageRequest;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;

@RestController
@RequestMapping("/api")
public class MeteoApiController {

  private final RealtimeIngestService ingest;
  private final MeteoObservationRepository repo;

  public MeteoApiController(RealtimeIngestService ingest, MeteoObservationRepository repo) {
    this.ingest = ingest;
    this.repo = repo;
  }

  @PostMapping("/ingest/realtime")
  public IngestResponse ingestNow() {
    int n = ingest.ingestRealtimeAndPublish();
    return new IngestResponse(n);
  }

  @GetMapping("/stations")
  public List<String> stations() {
    return repo.findDistinctStationIds();
  }

  @GetMapping("/latest")
  public List<MeteoObservation> latestForStation(@RequestParam String stationId,
                                                @RequestParam(defaultValue = "1") @Min(1) @Max(50) int limit) {
    return repo.findLatestByStation(stationId, PageRequest.of(0, limit));
  }

  @GetMapping("/series")
  public List<MeteoObservation> series(@RequestParam String stationId,
                                      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
                                      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to) {
    return repo.findSeries(stationId, from, to);
  }

  @GetMapping("/geo/latest")
  public List<MeteoObservation> latestWithGeo(@RequestParam(defaultValue = "60") @Min(1) @Max(1440) int minutes,
                                             @RequestParam(defaultValue = "500") @Min(1) @Max(5000) int limit) {
    Instant from = Instant.now().minus(minutes, ChronoUnit.MINUTES);
    return repo.findLatestWithGeo(from, PageRequest.of(0, limit));
  }

  public record IngestResponse(int inserted) {}
}
