#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "lcd1602.h"

static const char *TAG = "main";

// WiFi credentials — замінити на свої
#define WIFI_SSID "YOUR_SSID"
#define WIFI_PASS "YOUR_PASSWORD"

// I2C / LCD
#define I2C_SDA_PIN  GPIO_NUM_8
#define I2C_SCL_PIN  GPIO_NUM_9
#define LCD_I2C_ADDR 0x27   // або 0x3F якщо 0x27 не працює

extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "BKR firmware starting...");

    // NVS (потрібне для WiFi)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    // LCD ініціалізація
    LCD1602 lcd(I2C_SDA_PIN, I2C_SCL_PIN, LCD_I2C_ADDR);
    lcd.init();
    lcd.clear();
    lcd.print(0, 0, "BKR Starting...");

    ESP_LOGI(TAG, "LCD initialized");
    ESP_LOGI(TAG, "Ready");

    while (true) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
