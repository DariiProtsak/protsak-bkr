idf_component_register(
    SRCS "main.cpp"
    INCLUDE_DIRS "."
    REQUIRES lcd1602 driver esp_wifi nvs_flash
)
