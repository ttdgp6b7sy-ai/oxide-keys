use embedded_hal::pwm::SetDutyCycle;
use rp2040_hal::gpio::bank0::Gpio15;
use rp2040_hal::gpio::{FunctionNull, Pin, PullDown};
use rp2040_hal::pac::{PWM, RESETS};
use rp2040_hal::pwm::{FreeRunning, Pwm7, Slices};

const SYS_CLK_HZ: u32 = 125_000_000;

// buzzer on gp15, driven by pwm slice 7 channel b
pub struct Buzzer {
    slice: rp2040_hal::pwm::Slice<Pwm7, FreeRunning>,
}

impl Buzzer {
    pub fn new(pwm: PWM, resets: &mut RESETS, gpio15: Pin<Gpio15, FunctionNull, PullDown>) -> Self {
        let slices = Slices::new(pwm, resets);
        let mut slice = slices.pwm7;
        slice.default_config();
        slice.enable();
        slice.channel_b.output_to(gpio15);
        Self { slice }
    }

    // tone freq = clock / top, 50% duty = square wave
    pub fn tone(&mut self, freq_hz: u32) {
        let top = (SYS_CLK_HZ / freq_hz).min(u16::MAX as u32) as u16;
        self.slice.set_top(top);
        self.slice
            .channel_b
            .set_duty_cycle(top / 2)
            .expect("duty cycle is derived from top, so it's always in range");
    }

    pub fn stop(&mut self) {
        self.slice
            .channel_b
            .set_duty_cycle(0)
            .expect("zero duty cycle is always valid");
    }
}
