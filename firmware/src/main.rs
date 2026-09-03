#![no_std]
#![no_main]

use embedded_graphics::pixelcolor::Rgb565;
use embedded_graphics::prelude::RgbColor;
use embedded_hal::delay::DelayNs;
use embedded_hal::digital::OutputPin;
use panic_halt as _;
use rp2040_hal as hal;
use hal::clocks::Clock;
use hal::pac;

mod buzzer;
mod display;
mod encoder;
mod leds;
mod switches;

use switches::SwitchId;

#[link_section = ".boot2"]
#[used]
pub static BOOT2: [u8; 256] = rp2040_boot2::BOOT_LOADER_GENERIC_03H;

const XTAL_FREQ_HZ: u32 = 12_000_000;

#[rp2040_hal::entry]
fn main() -> ! {
    let mut peripherals = pac::Peripherals::take()
        .expect("RP2040 peripherals have already been taken");

    let mut watchdog = hal::Watchdog::new(peripherals.WATCHDOG);

    // clock setup, depends on the board's crystal
    let clocks = hal::clocks::init_clocks_and_plls(
        XTAL_FREQ_HZ,
        peripherals.XOSC,
        peripherals.CLOCKS,
        peripherals.PLL_SYS,
        peripherals.PLL_USB,
        &mut peripherals.RESETS,
        &mut watchdog,
    )
    .expect("failed to initialize RP2040 clocks; verify XTAL_FREQ_HZ");

    let mut timer =
        rp2040_hal::Timer::new(peripherals.TIMER, &mut peripherals.RESETS, &clocks);

    let sio = hal::Sio::new(peripherals.SIO);
    let pins = hal::gpio::Pins::new(
        peripherals.IO_BANK0,
        peripherals.PADS_BANK0,
        sio.gpio_bank0,
        &mut peripherals.RESETS,
    );

    let mut led = pins.gpio25.into_push_pull_output();

    // 8 panel switches switches.rs has the pin map
    let mut switches = switches::Switches::new(
        pins.gpio0.into_pull_up_input(),
        pins.gpio1.into_pull_up_input(),
        pins.gpio2.into_pull_up_input(),
        pins.gpio4.into_pull_up_input(),
        pins.gpio6.into_pull_up_input(),
        pins.gpio3.into_pull_up_input(),
        pins.gpio5.into_pull_up_input(),
        pins.gpio7.into_pull_up_input(),
    );

    let mut encoder = encoder::Encoder::new(
        pins.gpio10.into_pull_up_input(),
        pins.gpio8.into_pull_up_input(),
        pins.gpio9.into_push_pull_output(),
    );

    let mut buzzer =
        buzzer::Buzzer::new(peripherals.PWM, &mut peripherals.RESETS, pins.gpio15);

    buzzer.stop(); // stay quiet during startup

    // 2.4" ili9341 on spi0, miso wired but unused
    let mut display = display::build(
        peripherals.SPI0,
        &mut peripherals.RESETS,
        clocks.peripheral_clock.freq(),
        pins.gpio18, // SCK
        pins.gpio19, // MOSI
        pins.gpio16, // MISO
        pins.gpio17, // CS
        pins.gpio20, // DC
        pins.gpio21, // Reset
        pins.gpio22, // Backlight
        &mut timer,
    );

    let mut encoder_count = 0;
    let mut displayed_count = i32::MIN;
    let mut displayed_any_pressed = false;
    let mut number_buffer = [0u8; 8];

    loop {
        let now_ms = timer.get_counter().ticks() / 1000;
        switches.upd(now_ms);

        match encoder.upd() {
            encoder::Rot::Cw => encoder_count += 1,
            encoder::Rot::Ccw => encoder_count -= 1,
            encoder::Rot::None => {}
        }

        let any_pressed = SwitchId::ALL
            .iter()
            .any(|&switch_id| switches.pressed(switch_id));

        // led on if any switch is pressed
        if any_pressed {
            led.set_high()
                .expect("failed to set the status LED high");
        } else {
            led.set_low()
                .expect("failed to set the status LED low");
        }

        let display_changed =
            encoder_count != displayed_count || any_pressed != displayed_any_pressed;

        // redraw ~5x/sec, only if something actually changed
        if display_changed && now_ms % 200 < 20 {
            displayed_count = encoder_count;
            displayed_any_pressed = any_pressed;

            display.clear(Rgb565::BLACK);
            display.text("RP2040 PANEL", 10, 10, Rgb565::GREEN);

            for (index, switch_id) in SwitchId::ALL.iter().enumerate() {
                let color = if switches.pressed(*switch_id) {
                    Rgb565::GREEN
                } else {
                    Rgb565::new(15, 30, 15) // dim gray, RgbColor has no GRAY constant
                };

                display.dot(20 + (index as i32) * 26, 35, color);
            }

            display.text("ENC:", 10, 65, Rgb565::WHITE);
            display.text(
                format_number(encoder_count, &mut number_buffer),
                55,
                65,
                Rgb565::WHITE,
            );
        }

        timer.delay_ms(10);
    }
}

// no heap, so format ints by hand
fn format_number(number: i32, buffer: &mut [u8; 8]) -> &str {
    let is_negative = number < 0;
    let mut value = number.unsigned_abs();
    let mut index = buffer.len();

    if value == 0 {
        index -= 1;
        buffer[index] = b'0';
    }

    while value > 0 {
        index -= 1;
        buffer[index] = b'0' + (value % 10) as u8;
        value /= 10;
    }

    if is_negative {
        index -= 1;
        buffer[index] = b'-';
    }

    // always valid ascii
    core::str::from_utf8(&buffer[index..])
        .expect("number buffer contains only valid ASCII")
}
