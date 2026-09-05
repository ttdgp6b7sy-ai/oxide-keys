use embedded_hal::digital::{InputPin, OutputPin};
use rp2040_hal::gpio::bank0::*;
use rp2040_hal::gpio::{FunctionSioInput, FunctionSioOutput, Pin, PullUp};

// how long a switch reading has to stay the same before trust it (ms)
const DEBOUNCE_MS: u64 = 10;

#[derive(Clone, Copy, PartialEq)]
pub enum SwitchId {
    Sw1,
    Sw2,
    Sw3,
    Sw4,
    Sw5,
    Sw6,
    Sw7,
    Sw8,
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

// one switch, with debounce logic built in
struct DebouncedSwitch {
    on: bool,
    pending: bool,
    changed_at: u64,
}

impl DebouncedSwitch {
    fn new() -> Self {
        DebouncedSwitch {
            on: false,
            pending: false,
            changed_at: 0,
        }
    }

    fn update(&mut self, raw: bool, now: u64) {
        if raw != self.pending {
            // reading flipped, restart the debounce timer
            self.pending = raw;
            self.changed_at = now;
        } else if now.saturating_sub(self.changed_at) >= DEBOUNCE_MS {
            // been steady long enough, go ahead and trust it
            self.on = self.pending;
        }
    }

    fn on(&self) -> bool {
        self.on
    }
}

// gp0 does double duty: most of the time it reads sw1, but for a moment
// each update flip it to an output and pull it low so it can act as
// the ground pin for sw5 (which gets read back over on gp1)
enum Gpio0Mode {
    Input(Pin<Gpio0, FunctionSioInput, PullUp>),
    Output(Pin<Gpio0, FunctionSioOutput, PullUp>),
}

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
        Switches {
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

    // these all use pull-ups, so pressed means the pin reads low
    pub fn upd(&mut self, now: u64) {
        self.upd_shared(now);
        self.upd_std(now);
    }

    // sw1 and sw5 share gp0/gp1, so they need a couple extra steps
    fn upd_shared(&mut self, now: u64) {
        // this is always Some going in, put it back at the end
        let mode = self.gpio0.take().unwrap();

        // step 1: make sure gp0 is set as an input, then read sw1 off it
        let mut input_pin = match mode {
            Gpio0Mode::Input(pin) => pin,
            Gpio0Mode::Output(pin) => pin.into_pull_up_input(),
        };
        self.states[0].update(input_pin.is_low().unwrap(), now);

        // step 2: flip gp0 to an output and pull it low, this grounds sw5
        // so can read whether it's pressed over on gp1
        let mut output_pin = input_pin.into_push_pull_output();
        output_pin.set_low().unwrap();
        self.states[4].update(self.gpio1.is_low().unwrap(), now);

        self.gpio0 = Some(Gpio0Mode::Output(output_pin));
    }

    // the rest of the switches each have their own dedicated pin
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
