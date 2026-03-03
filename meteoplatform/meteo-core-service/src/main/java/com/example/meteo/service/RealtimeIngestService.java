package com.example.meteo.service;

import com.example.meteo.config.RabbitConfig;
import com.example.meteo.dto.RealtimeEvent;
import com.example.meteo.model.MeteoObservation;
import com.example.meteo.repository.MeteoObservationRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

@Service
public class RealtimeIngestService {

  private final TorinoMeteoClient client;
  private final MeteoObservationRepository repo;
  private final RabbitTemplate rabbitTemplate;
  private final ObjectMapper om = new ObjectMapper();

  @Value("${meteo.publish.enabled:true}")
  private boolean publishEnabled;

  public RealtimeIngestService(TorinoMeteoClient client, MeteoObservationRepository repo, RabbitTemplate rabbitTemplate) {
    this.client = client;
    this.repo = repo;
    this.rabbitTemplate = rabbitTemplate;
  }

  @Transactional
  public int ingestRealtimeAndPublish() {
    String raw = client.fetchRealtimeRaw();
    if (raw == null || raw.isBlank()) return 0;

    List<MeteoObservation> observations = new ArrayList<>();
    List<RealtimeEvent> events = new ArrayList<>();

    try {
      JsonNode root = om.readTree(raw);
      JsonNode arrayNode = findFirstArrayNode(root);
      if (arrayNode != null && arrayNode.isArray()) {
        for (JsonNode item : arrayNode) {
          Parsed p = parseItem(item, item.toString());
          MeteoObservation o = toEntity(p);
          observations.add(o);
          if (publishEnabled) events.add(toEvent(o));
        }
      } else {
        MeteoObservation o = new MeteoObservation();
        o.setObservedAt(Instant.now());
        o.setRawJson(raw);
        observations.add(o);
      }
    } catch (Exception e) {
      MeteoObservation o = new MeteoObservation();
      o.setObservedAt(Instant.now());
      o.setRawJson(raw);
      observations.add(o);
    }

    repo.saveAll(observations);

    if (publishEnabled) {
      for (RealtimeEvent ev : events) {
        rabbitTemplate.convertAndSend(RabbitConfig.QUEUE_NAME, ev);
      }
    }

    return observations.size();
  }

  private RealtimeEvent toEvent(MeteoObservation o) {
    return new RealtimeEvent(
        o.getStationId(),
        o.getStationName(),
        o.getCity(),
        o.getLat(),
        o.getLon(),
        o.getObservedAt(),
        o.getTemperature(),
        o.getRelativeHumidity(),
        o.getPressure()
    );
  }

  private MeteoObservation toEntity(Parsed p) {
    MeteoObservation o = new MeteoObservation();
    o.setStationId(p.stationId);
    o.setStationName(p.stationName);
    o.setCity(p.city);
    o.setLat(p.lat);
    o.setLon(p.lon);
    o.setObservedAt(p.observedAt != null ? p.observedAt : Instant.now());
    o.setTemperature(p.temperature);
    o.setRelativeHumidity(p.relativeHumidity);
    o.setPressure(p.pressure);
    o.setRawJson(p.rawJson);
    return o;
  }

  private static class Parsed {
    String stationId;
    String stationName;
    String city;
    Double lat;
    Double lon;
    Instant observedAt;
    Double temperature;
    Double relativeHumidity;
    Double pressure;
    String rawJson;
  }

  private Parsed parseItem(JsonNode item, String rawJson) {
    Parsed p = new Parsed();
    p.rawJson = rawJson;

    p.stationId = firstText(item, "station", "station_id", "id", "code", "codice");
    p.stationName = firstText(item, "station_name", "name", "nome", "stazione");
    p.city = firstText(item, "city", "comune", "localita", "location");

    p.lat = firstDouble(item, "lat", "latitude", "y");
    p.lon = firstDouble(item, "lon", "lng", "longitude", "x");

    // TorinoMeteo API nests station metadata under "station": {...}
    JsonNode st = item.get("station");
    if (st != null && st.isObject()) {
      if (p.stationId == null) p.stationId = firstText(st, "id", "station_id", "slug", "code", "codice");
      if (p.stationName == null) p.stationName = firstText(st, "name", "station_name", "nome", "stazione");
      if (p.city == null) p.city = firstText(st, "city", "comune", "localita", "location");
      if (p.lat == null) p.lat = firstDouble(st, "lat", "latitude", "y");
      if (p.lon == null) p.lon = firstDouble(st, "lng", "lon", "longitude", "x");
    }

    String ts = firstText(item, "datetime", "date_time", "timestamp", "time", "dataora");
    if (ts != null) p.observedAt = parseInstant(ts);

    p.temperature = firstDouble(item, "temperature", "temp", "t");
    p.relativeHumidity = firstDouble(item, "relative_humidity", "humidity", "rh", "umidita");
    p.pressure = firstDouble(item, "pressure", "pres", "p");

    return p;
  }

  private JsonNode findFirstArrayNode(JsonNode node) {
    if (node == null) return null;
    if (node.isArray()) return node;
    if (node.isObject()) {
      for (String key : new String[]{"data", "stations", "stazioni", "results"}) {
        JsonNode child = node.get(key);
        if (child != null && child.isArray()) return child;
      }
      Iterator<String> it = node.fieldNames();
      while (it.hasNext()) {
        JsonNode child = node.get(it.next());
        JsonNode found = findFirstArrayNode(child);
        if (found != null) return found;
      }
    }
    return null;
  }

  private static String firstText(JsonNode node, String... keys) {
    for (String k : keys) {
      JsonNode v = node.get(k);
      if (v != null && !v.isNull()) {
        String s = v.asText();
        if (s != null && !s.isBlank() && !"null".equalsIgnoreCase(s)) return s;
      }
    }
    return null;
  }

  private static Double firstDouble(JsonNode node, String... keys) {
    for (String k : keys) {
      JsonNode v = node.get(k);
      if (v != null && !v.isNull()) {
        if (v.isNumber()) return v.asDouble();
        String s = v.asText();
        try { if (s != null && !s.isBlank()) return Double.parseDouble(s); } catch (Exception ignored) {}
      }
    }
    return null;
  }

  private static Instant parseInstant(String ts) {
    try { return Instant.parse(ts); } catch (Exception ignored) {}
    try { return OffsetDateTime.parse(ts).toInstant(); } catch (Exception ignored) {}
    try {
      String normalized = ts.replace("T", " ").replace("/", "-");
      java.time.LocalDateTime ldt = java.time.LocalDateTime.parse(
          normalized, java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
      return ldt.toInstant(ZoneOffset.UTC);
    } catch (Exception ignored) {}
    return Instant.now();
  }
}
