#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "nvs_flash.h"
#include "lwip/ip4_addr.h"
#include "esp_timer.h"
#include "driver/uart.h"
#include "lcd1602.h"

static const char *TAG = "main";

#define I2C_SDA_PIN  GPIO_NUM_8
#define I2C_SCL_PIN  GPIO_NUM_9
#define LCD_I2C_ADDR 0x27

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static EventGroupHandle_t wifi_events;
static LCD1602 *lcd_ptr = nullptr;

static char lcd_line1[32] = "Connecting...   ";
static char lcd_line2[32] = "                ";
static volatile bool lcd_needs_update   = false;
static volatile bool csi_enabled        = false;
static volatile bool g_ctrl_disconnect  = false;

// ── CSI callback ─────────────────────────────────────────────────────────────
static void csi_callback(void *ctx, wifi_csi_info_t *data)
{
    int64_t ts_ms   = esp_timer_get_time() / 1000;
    int     n_pairs = data->len / 2;

    // JSONL: {"timestamp":...,"rssi":...,"csi":[[re,im],...]}
    printf("{\"timestamp\":%lld,\"rssi\":%d,\"csi\":[",
           (long long)ts_ms, (int)data->rx_ctrl.rssi);
    for (int k = 0; k < n_pairs; k++) {
        int8_t im = (int8_t)data->buf[2 * k];
        int8_t re = (int8_t)data->buf[2 * k + 1];
        if (k > 0) printf(",");
        printf("[%d,%d]", (int)re, (int)im);
    }
    printf("]}\n");

    snprintf(lcd_line2, sizeof(lcd_line2), "R:%-4d L:%-4d  ",
             (int)data->rx_ctrl.rssi, (int)data->len);
    lcd_needs_update = true;
}

// ── WiFi events ───────────────────────────────────────────────────────────────
static void wifi_event_handler(void *arg, esp_event_base_t base,
                                int32_t id, void *data)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();

    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        xEventGroupClearBits(wifi_events, WIFI_CONNECTED_BIT);
        if (!g_ctrl_disconnect) {
            strncpy(lcd_line1, "WiFi lost...    ", sizeof(lcd_line1) - 1);
            lcd_needs_update = true;
            esp_wifi_connect();
        }

    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *ev = (ip_event_got_ip_t *)data;
        char ip[16];
        esp_ip4addr_ntoa(&ev->ip_info.ip, ip, sizeof(ip));
        snprintf(lcd_line1, sizeof(lcd_line1), "%-16s", ip);
        lcd_needs_update = true;
        ESP_LOGI(TAG, "Got IP: %s", ip);
        xEventGroupSetBits(wifi_events, WIFI_CONNECTED_BIT);
    }
}

// ── WiFi init ─────────────────────────────────────────────────────────────────
static void wifi_init(const char *ssid, const char *pass)
{
    if (wifi_events == nullptr) {
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

        ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    }

    wifi_config_t wifi_cfg = {};
    strncpy((char *)wifi_cfg.sta.ssid,     ssid, sizeof(wifi_cfg.sta.ssid));
    strncpy((char *)wifi_cfg.sta.password, pass,  sizeof(wifi_cfg.sta.password));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());
}

// ── CSI ───────────────────────────────────────────────────────────────────────
static void csi_start(void)
{
    wifi_csi_config_t cfg = {};
    cfg.enable             = 1;
    cfg.acquire_csi_legacy = 1;
    cfg.acquire_csi_ht20   = 1;
    cfg.acquire_csi_ht40   = 1;
    cfg.acquire_csi_su     = 1;
    cfg.dump_ack_en        = 0;
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(csi_callback, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));
    csi_enabled = true;
    ESP_LOGI(TAG, "CSI + promiscuous enabled");
}

static void csi_stop(void)
{
    if (csi_enabled) {
        esp_wifi_set_csi(false);
        esp_wifi_set_promiscuous(false);
        csi_enabled = false;
    }
}

// ── UART command task ─────────────────────────────────────────────────────────
// Handles: WIFI_CONNECT:<ssid>:<password>
// Responds: WIFI_OK  |  WIFI_FAIL
static void uart_cmd_task(void *pv)
{
    // Install UART driver so uart_read_bytes() works reliably on UART0.
    // TX buffer = 0: printf() still writes directly to TX FIFO (no conflict).
    static const uart_port_t PORT = (uart_port_t)CONFIG_ESP_CONSOLE_UART_NUM;
    uart_driver_install(PORT, 512, 0, 0, NULL, 0);

    static char line[160];
    int     pos = 0;
    uint8_t ch;

    while (true) {
        int n = uart_read_bytes(PORT, &ch, 1,
                                pdMS_TO_TICKS(100));
        if (n <= 0) continue;
        if (ch == '\r') continue;

        if (ch == '\n') {
            if (pos == 0) continue;
            line[pos] = '\0';
            pos = 0;

            if (strncmp(line, "WIFI_CONNECT:", 13) == 0) {
                char *rest  = line + 13;
                char *colon = strchr(rest, ':');
                if (colon == NULL) {
                    printf("WIFI_FAIL\n");
                    continue;
                }
                *colon = '\0';
                const char *new_ssid = rest;
                const char *new_pass = colon + 1;

                ESP_LOGI(TAG, "WIFI_CONNECT ssid=%s", new_ssid);

                csi_stop();
                g_ctrl_disconnect = true;
                esp_wifi_disconnect();
                xEventGroupClearBits(wifi_events, WIFI_CONNECTED_BIT | WIFI_FAIL_BIT);

                wifi_config_t wifi_cfg = {};
                strncpy((char *)wifi_cfg.sta.ssid,     new_ssid, sizeof(wifi_cfg.sta.ssid));
                strncpy((char *)wifi_cfg.sta.password, new_pass,  sizeof(wifi_cfg.sta.password));
                ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg));

                strncpy(lcd_line1, "Connecting...   ", sizeof(lcd_line1) - 1);
                lcd_needs_update = true;

                g_ctrl_disconnect = false;
                esp_wifi_connect();

                EventBits_t bits = xEventGroupWaitBits(
                    wifi_events, WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
                    pdFALSE, pdFALSE, pdMS_TO_TICKS(15000));

                if (bits & WIFI_CONNECTED_BIT) {
                    printf("WIFI_OK\n");
                    csi_start();
                } else {
                    printf("WIFI_FAIL\n");
                    strncpy(lcd_line1, "WiFi fail!      ", sizeof(lcd_line1) - 1);
                    lcd_needs_update = true;
                }
            }
        } else if (pos < (int)sizeof(line) - 1) {
            line[pos++] = (char)ch;
        }
    }
}

// ── LCD task ──────────────────────────────────────────────────────────────────
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

// ── app_main ──────────────────────────────────────────────────────────────────
extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "BKR firmware v2.1 starting");

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    static LCD1602 lcd(I2C_SDA_PIN, I2C_SCL_PIN, LCD_I2C_ADDR);
    lcd.init();
    lcd.clear();
    lcd.print(0, 0, "BKR v2.1");
    lcd.print(0, 1, "WiFi init...");
    lcd_ptr = &lcd;
    vTaskDelay(pdMS_TO_TICKS(500));

    xTaskCreate(lcd_task,      "lcd_task",  2048, &lcd, 5, NULL);
    xTaskCreate(uart_cmd_task, "uart_cmd",  4096, NULL, 4, NULL);

    wifi_init("Darii", "darkosik");

    EventBits_t bits = xEventGroupWaitBits(wifi_events,
        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT, pdFALSE, pdFALSE,
        pdMS_TO_TICKS(15000));

    if (bits & WIFI_CONNECTED_BIT) {
        csi_start();
    } else {
        ESP_LOGW(TAG, "WiFi timeout — waiting for WIFI_CONNECT via UART");
        strncpy(lcd_line1, "Send WIFI cmd   ", sizeof(lcd_line1) - 1);
        lcd_needs_update = true;
    }

    while (true) {
        vTaskDelay(pdMS_TO_TICKS(5000));
    }
}
