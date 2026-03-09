package com.example.meteo.config;

import org.springframework.amqp.core.Queue;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.lang.NonNull;

@Configuration
public class RabbitConfig {
  public static final String QUEUE_NAME = "meteo.realtime";

  @Bean
  public Queue realtimeQueue() {
    return new Queue(QUEUE_NAME, true);
  }

  /**
   * Publish events as JSON so the Python analysis-service (aio-pika consumer)
   * can deserialize messages from RabbitMQ.
   */
  @Bean
  public MessageConverter messageConverter() {
    return new Jackson2JsonMessageConverter();
  }

  /**
   * Ensure the RabbitTemplate uses the JSON converter.
   * (Spring Boot will usually auto-wire this, but we make it explicit.)
   */
  @Bean
  public RabbitTemplate rabbitTemplate(@NonNull ConnectionFactory connectionFactory, @NonNull MessageConverter messageConverter) {
    RabbitTemplate template = new RabbitTemplate(connectionFactory);
    template.setMessageConverter(messageConverter);
    return template;
  }
}
