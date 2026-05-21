#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "nvs_flash.h"
#include "lwip/ip4_addr.h"
#include "lcd1602.h"

static const char *TAG = "main";

#define WIFI_SSID "Darii"
#define WIFI_PASS "darkosik"

#define I2C_SDA_PIN  GPIO_NUM_8
#define I2C_SCL_PIN  GPIO_NUM_9
#define LCD_I2C_ADDR 0x27

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static EventGroupHandle_t wifi_events;
static LCD1602 *lcd_ptr = nullptr;

// Буфери для LCD (32 байти — безпечно для snprintf, LCD показує перші 16)
static char lcd_line1[32] = "Connecting...   ";
static char lcd_line2[32] = "                ";
static volatile bool lcd_needs_update = false;

// ── CSI callback ────────────────────────────────────────────────────────────
static void csi_callback(void *ctx, wifi_csi_info_t *data)
{
    wifi_pkt_rx_ctrl_t *rx = &data->rx_ctrl;

    // Виводимо сирі дані у серійний порт
    printf("CSI|rssi:%d|noise:%d|len:%d|ch:%d|data:",
           rx->rssi, rx->noise_floor, data->len, rx->channel);
    for (int i = 0; i < data->len; i++) {
        printf("%d,", data->buf[i]);
    }
    printf("\n");

    // Оновлюємо рядок 2 LCD: RSSI + довжина CSI
    snprintf(lcd_line2, sizeof(lcd_line2), "R:%-4d L:%-4d  ", (int)rx->rssi, (int)data->len);
    lcd_needs_update = true;
}

// ── WiFi events ──────────────────────────────────────────────────────────────
static void wifi_event_handler(void *arg, esp_event_base_t base,
                                int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();

    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        strncpy(lcd_line1, "WiFi lost...    ", sizeof(lcd_line1) - 1);
        lcd_needs_update = true;
        esp_wifi_connect();

    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)data;
        char ip_str[16];
        esp_ip4addr_ntoa(&event->ip_info.ip, ip_str, sizeof(ip_str));
        snprintf(lcd_line1, sizeof(lcd_line1), "%-16s", ip_str);
        lcd_needs_update = true;
        ESP_LOGI(TAG, "Got IP: %s", ip_str);
        xEventGroupSetBits(wifi_events, WIFI_CONNECTED_BIT);
    }
}

// ── WiFi init ────────────────────────────────────────────────────────────────
static void wifi_init(void)
{
    wifi_events = xEventGroupCreate();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event_handler, NULL, NULL));

    wifi_config_t wifi_cfg = {};
    strncpy((char *)wifi_cfg.sta.ssid,     WIFI_SSID, sizeof(wifi_cfg.sta.ssid));
    strncpy((char *)wifi_cfg.sta.password, WIFI_PASS,  sizeof(wifi_cfg.sta.password));

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "Connecting to SSID: %s", WIFI_SSID);
}

// ── CSI init (після підключення до WiFi) ─────────────────────────────────────
static void csi_init(void)
{
    // ESP32-C6: wifi_csi_config_t = wifi_csi_acquire_config_t (MAC v2)
    wifi_csi_config_t csi_cfg = {};
    csi_cfg.enable              = 1;
    csi_cfg.acquire_csi_legacy  = 1;  // L-LTF (11g)
    csi_cfg.acquire_csi_ht20    = 1;  // HT-LTF HT20
    csi_cfg.acquire_csi_ht40    = 1;  // HT-LTF HT40
    csi_cfg.acquire_csi_su      = 1;  // HE-LTF SU
    csi_cfg.dump_ack_en         = 0;

    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi_cfg));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(csi_callback, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));
    ESP_LOGI(TAG, "CSI enabled");
}

// ── LCD update task ───────────────────────────────────────────────────────────
static void lcd_task(void *pvParam)
{
    LCD1602 *lcd = (LCD1602 *)pvParam;
    char prev1[17] = {}, prev2[17] = {};

    while (true) {
        if (lcd_needs_update) {
            lcd_needs_update = false;
            if (strcmp(prev1, lcd_line1) != 0) {
                lcd->print(0, 0, lcd_line1);
                memcpy(prev1, lcd_line1, sizeof(prev1));
            }
            if (strcmp(prev2, lcd_line2) != 0) {
                lcd->print(0, 1, lcd_line2);
                memcpy(prev2, lcd_line2, sizeof(prev2));
            }
        }
        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

// ── Точка входу ──────────────────────────────────────────────────────────────
extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "BKR firmware v1.0 starting");

    // NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    // LCD
    static LCD1602 lcd(I2C_SDA_PIN, I2C_SCL_PIN, LCD_I2C_ADDR);
    lcd.init();
    lcd.clear();
    lcd.print(0, 0, "BKR v1.0");
    lcd.print(0, 1, "WiFi init...");
    lcd_ptr = &lcd;
    vTaskDelay(pdMS_TO_TICKS(500));

    // LCD task
    xTaskCreate(lcd_task, "lcd_task", 2048, &lcd, 5, NULL);

    // WiFi
    wifi_init();

    // Чекаємо підключення
    EventBits_t bits = xEventGroupWaitBits(wifi_events,
        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT, pdFALSE, pdFALSE,
        pdMS_TO_TICKS(15000));

    if (bits & WIFI_CONNECTED_BIT) {
        csi_init();
    } else {
        ESP_LOGW(TAG, "WiFi connection timeout");
        strncpy(lcd_line1, "WiFi timeout!   ", sizeof(lcd_line1) - 1);
        strncpy(lcd_line2, "Check SSID/pass ", sizeof(lcd_line2) - 1);
        lcd_needs_update = true;
    }

    // Головний цикл — CSI надходить через callback
    uint32_t tick = 0;
    while (true) {
        if (tick % 10 == 0) {
            ESP_LOGI(TAG, "Running... (tick=%lu)", tick);
        }
        tick++;
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
