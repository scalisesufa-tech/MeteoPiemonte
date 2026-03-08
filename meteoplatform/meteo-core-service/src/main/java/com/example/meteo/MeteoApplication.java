package com.example.meteo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class MeteoApplication {
  public static void main(String[] args) {
    SpringApplication.run(MeteoApplication.class, args);
  }
}
