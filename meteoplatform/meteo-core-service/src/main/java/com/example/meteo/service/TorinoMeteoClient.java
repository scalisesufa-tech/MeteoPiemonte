package com.example.meteo.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Component
public class TorinoMeteoClient {
  private final RestTemplate rt = new RestTemplate();

  @Value("${meteo.torinometeo.realtimeUrl}")
  private String realtimeUrl;

  public String fetchRealtimeRaw() {
    return rt.getForObject(realtimeUrl, String.class);
  }
}
