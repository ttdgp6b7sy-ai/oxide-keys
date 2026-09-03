use embedded_hal::digital::OutputPin;
use rp2040_hal::gpio::bank0::{Gpio10, Gpio8, Gpio9};
use rp2040_hal::gpio::{FunctionSioInput, FunctionSioOutput, Pin, PullDown, PullUp};
use rotary_encoder_hal::{DefaultPhase, Direction, Rotary};

type PinA = Pin<Gpio10, FunctionSioInput, PullUp>;
type PinB = Pin<Gpio8, FunctionSioInput, PullUp>;
type GndPin = Pin<Gpio9, FunctionSioOutput, PullDown>;

// what happened since the last update
pub enum Rot {
    None,
    Cw,
    Ccw,
}

pub struct Encoder {
    rot: Rotary<PinA, PinB, DefaultPhase>,
    _gnd: GndPin, // gp9 is wired to the encoder's gnd pin
}

impl Encoder {
    pub fn new(pin_a: PinA, pin_b: PinB, mut gnd: GndPin) -> Self {
        gnd.set_low().unwrap(); // give the encoder a ground
        Self { rot: Rotary::new(pin_a, pin_b), _gnd: gnd }
    }

    pub fn upd(&mut self) -> Rot {
        match self.rot.update().unwrap() {
            Direction::Clockwise => Rot::Cw,
            Direction::CounterClockwise => Rot::Ccw,
            Direction::None => Rot::None,
        }
    }
}
