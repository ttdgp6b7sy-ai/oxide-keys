use embedded_hal::digital::{InputPin, OutputPin};
use rp2040_hal::gpio::bank0::*;
use rp2040_hal::gpio::{FunctionSioInput, FunctionSioOutput, Pin, PullUp};

// ignore changes shorter than this (button bounce)
const DEBOUNCE_MS: u64 = 10;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum SwitchId {
    Sw1 = 0,
    Sw2 = 1,
    Sw3 = 2,
    Sw4 = 3,
    Sw5 = 4,
    Sw6 = 5,
    Sw7 = 6,
    Sw8 = 7,
}

impl SwitchId {
    pub const ALL: [SwitchId; 8] = [
        SwitchId::Sw1,
        SwitchId::Sw2,
        SwitchId::Sw3,
        SwitchId::Sw4,
        SwitchId::Sw5,
        SwitchId::Sw6,
        SwitchId::Sw7,
        SwitchId::Sw8,
    ];
}

// one switch with bounce filtering
struct DebouncedSwitch {
    on: bool,
    pending: bool,
    changed_at: u64,
}

impl DebouncedSwitch {
    fn new() -> Self {
        Self { on: false, pending: false, changed_at: 0 }
    }

    fn update(&mut self, raw: bool, now: u64) {
        if raw != self.pending {
            // pin moved, restart the timer
            self.pending = raw;
            self.changed_at = now;
        } else if now.saturating_sub(self.changed_at) >= DEBOUNCE_MS {
            // stable long enough now, accept it
            self.on = self.pending;
        }
    }

    fn on(&self) -> bool {
        self.on
    }
}

// gp0 has two jobs: read sw1, or ground sw5. we swap its mode every update.
enum Gpio0Mode {
    Input(Pin<Gpio0, FunctionSioInput, PullUp>),
    Output(Pin<Gpio0, FunctionSioOutput, PullUp>),
}

// gpio reads/writes on this mcu don't actually fail; the pull-up input pins
// use Result<_, Infallible>, so unwrap() here is an assertion, not a risk
pub struct Switches {
    gpio0: Option<Gpio0Mode>,
    gpio1: Pin<Gpio1, FunctionSioInput, PullUp>,
    pin_sw2: Pin<Gpio2, FunctionSioInput, PullUp>,
    pin_sw3: Pin<Gpio4, FunctionSioInput, PullUp>,
    pin_sw4: Pin<Gpio6, FunctionSioInput, PullUp>,
    pin_sw6: Pin<Gpio3, FunctionSioInput, PullUp>,
    pin_sw7: Pin<Gpio5, FunctionSioInput, PullUp>,
    pin_sw8: Pin<Gpio7, FunctionSioInput, PullUp>,
    states: [DebouncedSwitch; 8],
}

impl Switches {
    pub fn new(
        gpio0: Pin<Gpio0, FunctionSioInput, PullUp>,
        gpio1: Pin<Gpio1, FunctionSioInput, PullUp>,
        pin_sw2: Pin<Gpio2, FunctionSioInput, PullUp>,
        pin_sw3: Pin<Gpio4, FunctionSioInput, PullUp>,
        pin_sw4: Pin<Gpio6, FunctionSioInput, PullUp>,
        pin_sw6: Pin<Gpio3, FunctionSioInput, PullUp>,
        pin_sw7: Pin<Gpio5, FunctionSioInput, PullUp>,
        pin_sw8: Pin<Gpio7, FunctionSioInput, PullUp>,
    ) -> Self {
        Self {
            gpio0: Some(Gpio0Mode::Input(gpio0)),
            gpio1,
            pin_sw2,
            pin_sw3,
            pin_sw4,
            pin_sw6,
            pin_sw7,
            pin_sw8,
            states: [
                DebouncedSwitch::new(),
                DebouncedSwitch::new(),
                DebouncedSwitch::new(),
                DebouncedSwitch::new(),
                DebouncedSwitch::new(),
                DebouncedSwitch::new(),
                DebouncedSwitch::new(),
                DebouncedSwitch::new(),
            ],
        }
    }

    // pull-ups: pressed = pin reads low
    pub fn upd(&mut self, now: u64) {
        self.upd_shared(now);
        self.upd_std(now);
    }

    // sw1 and sw5 share gp0/gp1
    fn upd_shared(&mut self, now: u64) {
        // the mode is always put back before this function returns, so this
        // can't actually stay empty across calls
        let mode = self.gpio0.take().expect("gpio0 mode not restored from last update");

        // 1. gp0 as input -> read sw1
        let mut input = match mode {
            Gpio0Mode::Input(pin) => pin,
            Gpio0Mode::Output(pin) => pin.into_pull_up_input(),
        };
        self.states[0].update(input.is_low().unwrap(), now);

        // 2. gp0 as output low -> it becomes the ground for sw5 (read on gp1)
        let mut output = input.into_push_pull_output();
        output.set_low().unwrap();
        self.states[4].update(self.gpio1.is_low().unwrap(), now);

        self.gpio0 = Some(Gpio0Mode::Output(output));
    }

    // all the switches with their own pin
    fn upd_std(&mut self, now: u64) {
        self.states[1].update(self.pin_sw2.is_low().unwrap(), now);
        self.states[2].update(self.pin_sw3.is_low().unwrap(), now);
        self.states[3].update(self.pin_sw4.is_low().unwrap(), now);
        self.states[5].update(self.pin_sw6.is_low().unwrap(), now);
        self.states[6].update(self.pin_sw7.is_low().unwrap(), now);
        self.states[7].update(self.pin_sw8.is_low().unwrap(), now);
    }

    pub fn pressed(&self, switch: SwitchId) -> bool {
        self.states[switch as usize].on()
    }
}
