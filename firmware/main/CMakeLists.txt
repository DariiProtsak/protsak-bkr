idf_component_register(
    SRCS "main.cpp"
    INCLUDE_DIRS "."
    REQUIRES lcd1602 driver esp_wifi esp_netif esp_event nvs_flash esp_timer
)
