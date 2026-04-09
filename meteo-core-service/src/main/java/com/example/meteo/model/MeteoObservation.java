package com.example.meteo.model;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "meteo_observation")
public class MeteoObservation {
  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(name = "station_id")
  private String stationId;

  @Column(name = "station_name")
  private String stationName;

  private String city;

  private Double lat;
  private Double lon;

  @Column(name = "observed_at", nullable = false)
  private Instant observedAt;

  private Double temperature;

  @Column(name = "relative_humidity")
  private Double relativeHumidity;

  private Double pressure;

  @Column(name = "raw_json", columnDefinition = "TEXT")
  private String rawJson;

  public Long getId() { return id; }
  public String getStationId() { return stationId; }
  public void setStationId(String stationId) { this.stationId = stationId; }
  public String getStationName() { return stationName; }
  public void setStationName(String stationName) { this.stationName = stationName; }
  public String getCity() { return city; }
  public void setCity(String city) { this.city = city; }
  public Double getLat() { return lat; }
  public void setLat(Double lat) { this.lat = lat; }
  public Double getLon() { return lon; }
  public void setLon(Double lon) { this.lon = lon; }
  public Instant getObservedAt() { return observedAt; }
  public void setObservedAt(Instant observedAt) { this.observedAt = observedAt; }
  public Double getTemperature() { return temperature; }
  public void setTemperature(Double temperature) { this.temperature = temperature; }
  public Double getRelativeHumidity() { return relativeHumidity; }
  public void setRelativeHumidity(Double relativeHumidity) { this.relativeHumidity = relativeHumidity; }
  public Double getPressure() { return pressure; }
  public void setPressure(Double pressure) { this.pressure = pressure; }
  public String getRawJson() { return rawJson; }
  public void setRawJson(String rawJson) { this.rawJson = rawJson; }
}
