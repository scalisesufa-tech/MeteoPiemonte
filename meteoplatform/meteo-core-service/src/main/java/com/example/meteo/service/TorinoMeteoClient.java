package com.example.meteo.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Component
public class TorinoMeteoClient {
  private static final Logger log = LoggerFactory.getLogger(TorinoMeteoClient.class);
  private final RestTemplate rt = new RestTemplate();
  private final ObjectMapper mapper = new ObjectMapper();

  private List<Municipality> municipalities = new ArrayList<>();

  public record Municipality(String id, String name, Double lat, Double lon) {
  }

  @PostConstruct
  public void init() {
    try (InputStream is = getClass().getResourceAsStream("/comuni_piemonte.json")) {
      if (is != null) {
        List<Municipality> all = mapper.readValue(is, new TypeReference<List<Municipality>>() {
        });
        municipalities = all.stream()
            .filter(m -> m.id().startsWith("001"))
            .limit(100)
            .collect(Collectors.toList());
        log.info("Loaded {} municipalities from Turin province (filtered from {})", municipalities.size(), all.size());
      } else {
        log.error("Could not find comuni_piemonte.json in resources");
      }
    } catch (Exception e) {
      log.error("Error loading municipalities list: {}", e.getMessage(), e);
    }
  }

  public String fetchRealtimeRaw() {
    if (municipalities.isEmpty()) {
      log.warn("No municipalities loaded, skipping fetch");
      return "[]";
    }

    log.info("Fetching data from Open-Meteo for {} locations in batches of 50", municipalities.size());
    ArrayNode root = mapper.createArrayNode();

    int batchSize = 50;
    for (int i = 0; i < municipalities.size(); i += batchSize) {
      int end = Math.min(i + batchSize, municipalities.size());
      List<Municipality> batch = municipalities.subList(i, end);
      fetchBatch(batch, root);

      if (end < municipalities.size()) {
        try {
          Thread.sleep(5000);
        } catch (InterruptedException e) {
          Thread.currentThread().interrupt();
        }
      }
    }

    log.info("Total observations collected: {}", root.size());
    return root.toString();
  }

  private void fetchBatch(List<Municipality> batch, ArrayNode root) {
    try {
      String lats = batch.stream().map(m -> String.valueOf(m.lat())).collect(Collectors.joining(","));
      String lons = batch.stream().map(m -> String.valueOf(m.lon())).collect(Collectors.joining(","));

      String url = String.format(
          "https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,relative_humidity_2m,surface_pressure",
          lats, lons);

      JsonNode resp = rt.getForObject(url, JsonNode.class);

      if (resp != null && resp.isArray()) {
        for (int j = 0; j < resp.size(); j++) {
          processResponseNode(resp.get(j), batch.get(j), root);
        }
      } else if (resp != null && resp.isObject() && batch.size() == 1) {
        processResponseNode(resp, batch.get(0), root);
      }
    } catch (Exception e) {
      log.error("Error fetching batch of size {}: {}", batch.size(), e.getMessage());
    }
  }

  private void processResponseNode(JsonNode node, Municipality m, ArrayNode root) {
    JsonNode current = node.get("current");
    if (current != null) {
      ObjectNode item = mapper.createObjectNode();
      ObjectNode station = item.putObject("station");
      station.put("id", m.id());
      station.put("name", m.name());
      station.put("city", m.name());
      station.put("lat", m.lat());
      station.put("lng", m.lon());

      if (current.has("temperature_2m"))
        item.put("temperature", current.get("temperature_2m").asDouble());
      if (current.has("relative_humidity_2m"))
        item.put("relative_humidity", current.get("relative_humidity_2m").asDouble());
      if (current.has("surface_pressure"))
        item.put("pressure", current.get("surface_pressure").asDouble());

      item.put("datetime", current.get("time").asText() + ":00Z");
      root.add(item);
    }
  }
}
