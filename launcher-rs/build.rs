//! Embed the Falco icon into Windows launcher stubs.
//!
//! Launchers are prebuilt stubs with their configuration appended, so the icon
//! has to live in the stub itself: embedding it here means every launcher the
//! editor generates for Windows inherits it. Other platforms cannot carry
//! executable icons (macOS launchers are terminal binaries and ELF has no icon
//! slot), so this is Windows-only.

fn main() {
    #[cfg(windows)]
    {
        let mut resource = winresource::WindowsResource::new();
        resource.set_icon("../editor/assets/falco.ico");
        resource
            .compile()
            .expect("failed to embed editor/assets/falco.ico into falco-stub");
    }
}
