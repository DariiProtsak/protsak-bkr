#include "lcd1602.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

static const char *TAG = "lcd1602";

// HD44780 команди
#define LCD_CMD_CLEAR       0x01
#define LCD_CMD_HOME        0x02
#define LCD_CMD_ENTRY_MODE  0x06
#define LCD_CMD_DISPLAY_ON  0x0C
#define LCD_CMD_FUNC_SET    0x28  // 4-bit, 2 рядки, 5x8
#define LCD_CMD_DDRAM       0x80

// PCF8574 біти (I2C-backpack HW-61)
#define BIT_RS   0x01
#define BIT_RW   0x02
#define BIT_EN   0x04
#define BIT_BL   0x08
#define BIT_D4   0x10
#define BIT_D5   0x20
#define BIT_D6   0x40
#define BIT_D7   0x80

// Адреси рядків
static const uint8_t ROW_ADDR[] = {0x00, 0x40};

LCD1602::LCD1602(gpio_num_t sda, gpio_num_t scl, uint8_t addr)
    : sda_(sda), scl_(scl), addr_(addr), bus_(nullptr), dev_(nullptr) {}

LCD1602::~LCD1602()
{
    if (dev_) i2c_master_bus_rm_device(dev_);
    if (bus_) i2c_del_master_bus(bus_);
}

void LCD1602::init()
{
    i2c_master_bus_config_t bus_cfg = {
        .i2c_port      = I2C_NUM_0,
        .sda_io_num    = sda_,
        .scl_io_num    = scl_,
        .clk_source    = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags = { .enable_internal_pullup = true },
    };
    ESP_ERROR_CHECK(i2c_new_master_bus(&bus_cfg, &bus_));

    i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address  = addr_,
        .scl_speed_hz    = 100000,
    };
    ESP_ERROR_CHECK(i2c_master_bus_add_device(bus_, &dev_cfg, &dev_));

    vTaskDelay(pdMS_TO_TICKS(50));

    // Ініціалізація в 4-бітному режимі (за специфікацією HD44780)
    write4bits(0x30);
    vTaskDelay(pdMS_TO_TICKS(5));
    write4bits(0x30);
    vTaskDelay(pdMS_TO_TICKS(1));
    write4bits(0x30);
    vTaskDelay(pdMS_TO_TICKS(1));
    write4bits(0x20);  // перехід на 4-bit
    vTaskDelay(pdMS_TO_TICKS(1));

    sendByte(LCD_CMD_FUNC_SET,    false);
    sendByte(LCD_CMD_DISPLAY_ON,  false);
    sendByte(LCD_CMD_CLEAR,       false);
    vTaskDelay(pdMS_TO_TICKS(2));
    sendByte(LCD_CMD_ENTRY_MODE,  false);

    ESP_LOGI(TAG, "LCD1602 initialized (addr=0x%02X, SDA=%d, SCL=%d)", addr_, sda_, scl_);
}

void LCD1602::clear()
{
    sendByte(LCD_CMD_CLEAR, false);
    vTaskDelay(pdMS_TO_TICKS(2));
}

void LCD1602::setCursor(uint8_t col, uint8_t row)
{
    if (row > 1) row = 1;
    if (col > 15) col = 15;
    sendByte(LCD_CMD_DDRAM | (ROW_ADDR[row] + col), false);
}

void LCD1602::print(uint8_t col, uint8_t row, const char *text)
{
    setCursor(col, row);
    while (*text) {
        sendByte((uint8_t)*text++, true);
    }
}

void LCD1602::backlight(bool on)
{
    backlight_ = on;
    // Надсилаємо 0 щоб оновити стан підсвічування
    uint8_t val = backlight_ ? BIT_BL : 0x00;
    i2c_master_transmit(dev_, &val, 1, 100);
}

void LCD1602::sendByte(uint8_t data, bool rs)
{
    sendNibble(data >> 4, rs ? BIT_RS : 0);
    sendNibble(data & 0x0F, rs ? BIT_RS : 0);
}

void LCD1602::sendNibble(uint8_t nibble, uint8_t flags)
{
    uint8_t hi = flags | (backlight_ ? BIT_BL : 0);
    if (nibble & 0x01) hi |= BIT_D4;
    if (nibble & 0x02) hi |= BIT_D5;
    if (nibble & 0x04) hi |= BIT_D6;
    if (nibble & 0x08) hi |= BIT_D7;

    uint8_t buf[2] = { (uint8_t)(hi | BIT_EN), hi };
    i2c_master_transmit(dev_, buf, 2, 100);
    vTaskDelay(pdMS_TO_TICKS(1));
}

void LCD1602::write4bits(uint8_t nibble)
{
    uint8_t val = (backlight_ ? BIT_BL : 0);
    if (nibble & 0x10) val |= BIT_D4;
    if (nibble & 0x20) val |= BIT_D5;
    if (nibble & 0x40) val |= BIT_D6;
    if (nibble & 0x80) val |= BIT_D7;

    uint8_t buf[2] = { (uint8_t)(val | BIT_EN), val };
    i2c_master_transmit(dev_, buf, 2, 100);
    vTaskDelay(pdMS_TO_TICKS(1));
}
