use display_interface_spi::SPIInterface;
use embedded_graphics::mono_font::{ascii::FONT_6X10, MonoTextStyle};
use embedded_graphics::pixelcolor::Rgb565;
use embedded_graphics::prelude::*;
use embedded_graphics::primitives::{Circle, PrimitiveStyle};
use embedded_graphics::text::Text;
use embedded_hal::delay::DelayNs;
use embedded_hal::digital::OutputPin;
use embedded_hal_bus::spi::ExclusiveDevice;
use ili9341::{DisplaySize240x320, Ili9341, Orientation};
use rp2040_hal::fugit::{HertzU32, RateExtU32};
use rp2040_hal::gpio::bank0::{Gpio16, Gpio17, Gpio18, Gpio19, Gpio20, Gpio21, Gpio22};
use rp2040_hal::gpio::{FunctionNull, FunctionSioOutput, FunctionSpi, Pin, PullDown};
use rp2040_hal::pac::{RESETS, SPI0};
use rp2040_hal::spi::Spi;

// wraps the ili9341 driver plus the backlight pin so main.rs doesn't have
// to know about the driver's generic types
pub struct Lcd<DI, RST>
where
    DI: display_interface::WriteOnlyDataCommand,
    RST: OutputPin,
{
    drv: Ili9341<DI, RST>,
    bl: Pin<Gpio22, FunctionSioOutput, PullDown>,
}

pub fn build(
    spi0: SPI0,
    resets: &mut RESETS,
    peri_clock_freq: HertzU32,
    sck: Pin<Gpio18, FunctionNull, PullDown>,
    mosi: Pin<Gpio19, FunctionNull, PullDown>,
    miso: Pin<Gpio16, FunctionNull, PullDown>,
    cs: Pin<Gpio17, FunctionNull, PullDown>,
    dc: Pin<Gpio20, FunctionNull, PullDown>,
    rst: Pin<Gpio21, FunctionNull, PullDown>,
    bl: Pin<Gpio22, FunctionNull, PullDown>,
    delay: &mut impl DelayNs,
) -> Lcd<impl display_interface::WriteOnlyDataCommand, Pin<Gpio21, FunctionSioOutput, PullDown>> {
    let spi_pins = (
        mosi.into_function::<FunctionSpi>(),
        miso.into_function::<FunctionSpi>(),
        sck.into_function::<FunctionSpi>(),
    );

    // 16 MHz seems to be the sweet spot for this panel, anything higher gets flaky
    let spi_bus = Spi::<_, _, _, 8>::new(spi0, spi_pins).init(
        resets,
        peri_clock_freq,
        16.MHz(),
        embedded_hal::spi::MODE_0,
    );

    // only device on this bus, so no need to share
    let spi_device = ExclusiveDevice::new_no_delay(spi_bus, cs.into_push_pull_output())
        .expect("could not set up the display cs pin");

    let iface = SPIInterface::new(spi_device, dc.into_push_pull_output());

    let mut drv = Ili9341::new(
        iface,
        rst.into_push_pull_output(),
        delay,
        Orientation::Portrait,
        DisplaySize240x320,
    )
    .expect("ili9341 init failed, double check the wiring");

    drv.clear(Rgb565::BLACK).expect("initial clear failed");

    let mut bl = bl.into_push_pull_output();
    bl.set_high().unwrap();

    Lcd { drv, bl }
}

impl<DI, RST> Lcd<DI, RST>
where
    DI: display_interface::WriteOnlyDataCommand,
    RST: OutputPin,
{
    pub fn clear(&mut self, color: Rgb565) {
        self.drv.clear(color).expect("display clear failed");
    }

    pub fn text(&mut self, s: &str, x: i32, y: i32, color: Rgb565) {
        let style = MonoTextStyle::new(&FONT_6X10, color);
        Text::new(s, Point::new(x, y), style)
            .draw(&mut self.drv)
            .expect("failed to draw text");
    }

    pub fn dot(&mut self, x: i32, y: i32, color: Rgb565) {
        Circle::new(Point::new(x, y), 12)
            .into_styled(PrimitiveStyle::with_fill(color))
            .draw(&mut self.drv)
            .expect("failed to draw dot");
    }
}
