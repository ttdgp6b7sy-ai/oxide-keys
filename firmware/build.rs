use std::env;
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;

// copy memory.x next to the build output so the linker finds it
fn main() {
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());
    File::create(out.join("memory.x"))
        .unwrap()
        .write_all(include_bytes!("memory.x"))
        .unwrap();
    println!("cargo:rustc-link-search={}", out.display());
}
