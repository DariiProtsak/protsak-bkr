#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "nvs_flash.h"
#include "lwip/ip4_addr.h"
#include "lwip/sockets.h"
#include "lwip/inet.h"
#include "esp_timer.h"
#include "esp_rom_uart.h"
#include "mbedtls/base64.h"
#include "lcd1602.h"

static const char *TAG = "main";

#define I2C_SDA_PIN  GPIO_NUM_8
#define I2C_SCL_PIN  GPIO_NUM_9
#define LCD_I2C_ADDR 0x27

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

// ── CSI queue ─────────────────────────────────────────────────────────────────
// Decouples WiFi task (callback) from UART output task so no packets are dropped
#define CSI_BUF_MAX  256
#define CSI_QUEUE_LEN 32

typedef struct {
    int64_t ts_ms;
    int8_t  rssi;
    int     len;          // bytes in buf (always even; pairs = len/2)
    int8_t  buf[CSI_BUF_MAX];
} csi_event_t;

static QueueHandle_t csi_queue = NULL;

static EventGroupHandle_t wifi_events;
static LCD1602 *lcd_ptr = nullptr;

static char lcd_line1[32] = "Connecting...   ";
static char lcd_line2[32] = "                ";
static volatile bool lcd_needs_update  = false;
static volatile bool csi_enabled       = false;
static volatile bool     g_ctrl_disconnect = false;
static volatile uint32_t g_csi_count       = 0;
static volatile bool     wifi_ready        = false;   // set after esp_wifi_start()


// ── CSI callback — runs in WiFi task context, must be fast ───────────────────
static void csi_callback(void *ctx, wifi_csi_info_t *data)
{
    csi_event_t evt;
    evt.ts_ms = esp_timer_get_time() / 1000;
    evt.rssi  = (int8_t)data->rx_ctrl.rssi;
    evt.len   = (data->len <= CSI_BUF_MAX) ? data->len : CSI_BUF_MAX;
    memcpy(evt.buf, data->buf, evt.len);
    xQueueSend(csi_queue, &evt, 0);   // non-blocking, drop if full
    g_csi_count++;
}

// ── CSI output task — Base64-encoded raw bytes, ~35% smaller than decimal JSON ─
static void csi_output_task(void *pv)
{
    csi_event_t evt;
    static char b64[400];
    static char out[512];
    while (true) {
        if (xQueueReceive(csi_queue, &evt, portMAX_DELAY) != pdTRUE) continue;
        size_t b64_len = 0;
        mbedtls_base64_encode((unsigned char *)b64, sizeof(b64), &b64_len,
                              (const unsigned char *)evt.buf, evt.len);
        b64[b64_len] = '\0';
        snprintf(out, sizeof(out),
                 "{\"timestamp\":%lld,\"rssi\":%d,\"csi\":\"%s\"}\n",
                 (long long)evt.ts_ms, (int)evt.rssi, b64);
        printf("%s", out);
    }
}

// ── UDP TX task — sends 250 pkt/s to gateway to trigger 802.11 ACK → CSI ────
static void udp_tx_task(void *pv)
{
    xEventGroupWaitBits(wifi_events, WIFI_CONNECTED_BIT, pdFALSE, pdFALSE, portMAX_DELAY);
    vTaskDelay(pdMS_TO_TICKS(500));

    char gw_str[16] = "192.168.1.1";
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    if (netif) {
        esp_netif_ip_info_t info = {};
        if (esp_netif_get_ip_info(netif, &info) == ESP_OK)
            esp_ip4addr_ntoa(&info.gw, gw_str, sizeof(gw_str));
    }
    ESP_LOGI(TAG, "DNS ping → %s:53 @ 50 Hz", gw_str);

    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    struct sockaddr_in dest = {};
    dest.sin_family = AF_INET;
    dest.sin_port   = htons(53);  // DNS — router replies with a real data frame → CSI
    inet_aton(gw_str, &dest.sin_addr);

    // Minimal DNS query for "a." — varies transaction ID so router replies every time
    uint8_t dns_pkt[] = {
        0x00, 0x00,                          // transaction ID (incremented below)
        0x01, 0x00,                          // standard query, recursion desired
        0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x01, 'a',  0x00,                    // name: "a."
        0x00, 0x01, 0x00, 0x01               // type A, class IN
    };
    uint16_t tid = 0;
    while (true) {
        if (csi_enabled) {
            tid++;
            dns_pkt[0] = (tid >> 8) & 0xFF;
            dns_pkt[1] = tid & 0xFF;
            sendto(sock, dns_pkt, sizeof(dns_pkt), 0, (struct sockaddr *)&dest, sizeof(dest));
        }
        vTaskDelay(20);  // 20ms = 50 Hz
    }
}

// ── RSSI monitor task — updates LCD line 2 every 500 ms ──────────────────────
static void rssi_monitor_task(void *pv)
{
    uint32_t last = 0;
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(500));
        wifi_ap_record_t ap = {};
        if (esp_wifi_sta_get_ap_info(&ap) != ESP_OK) continue;
        uint32_t cur   = g_csi_count;
        uint32_t rate  = (cur - last) * 2;   // packets per second (500 ms interval)
        last           = cur;
        snprintf(lcd_line2, sizeof(lcd_line2), "%-4ddBm  %3lu pkt/s",
                 (int)ap.rssi, (unsigned long)rate);
        lcd_needs_update = true;
        ESP_LOGI(TAG, "CSI %lu pkt/s | RSSI %d dBm", (unsigned long)rate, (int)ap.rssi);
    }
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
        printf("{\"ip\":\"%s\"}\n", ip);
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
        // Force HT20 (802.11n) — without this ESP32-C5 uses HE (WiFi 6) and
        // dump_ack_en CSI only fires for HT/legacy frames, not HE ACKs
        esp_err_t proto_err = esp_wifi_set_protocol(WIFI_IF_STA,
            WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N);
        if (proto_err == ESP_OK) {
            esp_wifi_set_bandwidth(WIFI_IF_STA, WIFI_BW_HT20);
            ESP_LOGI(TAG, "WiFi forced to HT20 mode");
        } else {
            ESP_LOGW(TAG, "set_protocol HT failed: %s", esp_err_to_name(proto_err));
        }
    }

    wifi_config_t wifi_cfg = {};
    strncpy((char *)wifi_cfg.sta.ssid,     ssid, sizeof(wifi_cfg.sta.ssid));
    strncpy((char *)wifi_cfg.sta.password, pass,  sizeof(wifi_cfg.sta.password));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());
    wifi_ready = true;
}

// ── CSI start / stop ──────────────────────────────────────────────────────────
static void csi_start(void)
{
    wifi_csi_config_t cfg = {};
    cfg.enable             = 1;
    cfg.acquire_csi_legacy = 1;
    cfg.acquire_csi_ht20   = 1;
    cfg.acquire_csi_ht40   = 1;
    cfg.acquire_csi_su     = 1;  // HE SU (WiFi 6 / 802.11ax) — критично для сучасних роутерів
    cfg.acquire_csi_mu     = 1;  // HE MU
    cfg.dump_ack_en        = 1;
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(csi_callback, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));
    csi_enabled = true;
    ESP_LOGI(TAG, "CSI enabled (HT20 mode)");
}

static void csi_stop(void)
{
    if (csi_enabled) {
        esp_wifi_set_csi(false);
        csi_enabled = false;
    }
}

// ── UART command task ─────────────────────────────────────────────────────────
// Uses ROM UART RX (no driver install) to avoid console UART driver conflicts.
// Response via printf → VFS → ROM UART TX, same path as ESP_LOGI.
#define UART_REPLY(msg) do { printf(msg "\n"); fflush(stdout); } while(0)

static void uart_cmd_task(void *pv)
{
    static char line[160];
    int     pos = 0;
    uint8_t ch  = 0;

    while (true) {
        vTaskDelay(2);   // 2 ticks (~20ms at 100Hz) — pdMS_TO_TICKS(1)=0 on 100Hz, so use ticks directly
        if (esp_rom_uart_rx_one_char(&ch) != 0) continue;
        if (ch == '\r') continue;

        if (ch == '\n') {
            if (pos == 0) continue;
            line[pos] = '\0';
            pos = 0;

            if (strncmp(line, "WIFI_CONNECT:", 13) == 0) {
                if (!wifi_ready) { UART_REPLY("WIFI_FAIL"); continue; }
                char *rest  = line + 13;
                char *colon = strchr(rest, ':');
                if (colon == NULL) { UART_REPLY("WIFI_FAIL"); continue; }
                *colon = '\0';
                const char *new_ssid = rest;
                const char *new_pass = colon + 1;

                ESP_LOGI(TAG, "WIFI_CONNECT ssid=%s", new_ssid);

                // Already connected to same SSID — reply immediately
                wifi_ap_record_t ap_info = {};
                if (esp_wifi_sta_get_ap_info(&ap_info) == ESP_OK &&
                    strcmp((char *)ap_info.ssid, new_ssid) == 0) {
                    ESP_LOGI(TAG, "Already connected to %s", new_ssid);
                    UART_REPLY("WIFI_OK");
                    if (!csi_enabled) csi_start();
                    continue;
                }

                csi_stop();
                g_ctrl_disconnect = true;
                esp_wifi_disconnect();
                xEventGroupClearBits(wifi_events, WIFI_CONNECTED_BIT | WIFI_FAIL_BIT);

                wifi_config_t wifi_cfg = {};
                strncpy((char *)wifi_cfg.sta.ssid,     new_ssid, sizeof(wifi_cfg.sta.ssid));
                strncpy((char *)wifi_cfg.sta.password, new_pass,  sizeof(wifi_cfg.sta.password));
                if (esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg) != ESP_OK) {
                    UART_REPLY("WIFI_FAIL");
                    g_ctrl_disconnect = false;
                    continue;
                }

                strncpy(lcd_line1, "Connecting...   ", sizeof(lcd_line1) - 1);
                lcd_needs_update = true;

                g_ctrl_disconnect = false;
                esp_wifi_connect();

                EventBits_t bits = xEventGroupWaitBits(
                    wifi_events, WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
                    pdFALSE, pdFALSE, pdMS_TO_TICKS(15000));

                if (bits & WIFI_CONNECTED_BIT) {
                    UART_REPLY("WIFI_OK");
                    csi_start();
                } else {
                    UART_REPLY("WIFI_FAIL");
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
    ESP_LOGI(TAG, "BKR firmware v2.3 starting");

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    csi_queue = xQueueCreate(CSI_QUEUE_LEN, sizeof(csi_event_t));

    static LCD1602 lcd(I2C_SDA_PIN, I2C_SCL_PIN, LCD_I2C_ADDR);
    lcd.init();
    lcd.clear();
    lcd.print(0, 0, "BKR v2.3");
    lcd.print(0, 1, "WiFi init...");
    lcd_ptr = &lcd;
    vTaskDelay(pdMS_TO_TICKS(500));

    xTaskCreate(lcd_task,        "lcd_task",   2048, &lcd, 5, NULL);
    xTaskCreate(csi_output_task, "csi_out",   4096, NULL, 6, NULL);
    xTaskCreate(uart_cmd_task,   "uart_cmd",  4096, NULL, 4, NULL);
    xTaskCreate(rssi_monitor_task,"rssi_mon", 2048, NULL, 3, NULL);

    wifi_init("Darii", "darkosik");

    xTaskCreate(udp_tx_task,     "udp_tx",    3072, NULL, 5, NULL);

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
