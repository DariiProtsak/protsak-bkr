#pragma once
#include "driver/i2c_master.h"
#include "driver/gpio.h"

class LCD1602 {
public:
    LCD1602(gpio_num_t sda, gpio_num_t scl, uint8_t addr = 0x27);
    ~LCD1602();

    void init();
    void clear();
    void print(uint8_t col, uint8_t row, const char *text);
    void createChar(uint8_t location, const uint8_t *pattern);
    void setCursor(uint8_t col, uint8_t row);
    void backlight(bool on);

private:
    gpio_num_t sda_;
    gpio_num_t scl_;
    uint8_t    addr_;

    i2c_master_bus_handle_t  bus_;
    i2c_master_dev_handle_t  dev_;

    void sendByte(uint8_t data, bool rs);
    void sendNibble(uint8_t nibble, uint8_t flags);
    void write4bits(uint8_t val);

    bool backlight_ = true;
};
