package com.example.meteo.repository;

import com.example.meteo.model.MeteoObservation;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.Instant;
import java.util.List;

public interface MeteoObservationRepository extends JpaRepository<MeteoObservation, Long> {

  @Query("select distinct o.stationId from MeteoObservation o where o.stationId is not null")
  List<String> findDistinctStationIds();

  @Query("select o from MeteoObservation o where o.stationId = :stationId and o.observedAt between :from and :to order by o.observedAt asc")
  List<MeteoObservation> findSeries(String stationId, Instant from, Instant to);

  @Query("select o from MeteoObservation o where o.stationId = :stationId order by o.observedAt desc")
  List<MeteoObservation> findLatestByStation(String stationId, Pageable pageable);

  @Query("select o from MeteoObservation o where o.lat is not null and o.lon is not null and o.observedAt >= :from order by o.observedAt desc")
  List<MeteoObservation> findLatestWithGeo(Instant from, Pageable pageable);
}
