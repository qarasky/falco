//! Guard the icon asset that `build.rs` embeds into Windows launchers.

#[test]
fn windows_launcher_icon_asset_is_a_real_ico() {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../editor/assets/falco.ico");
    let bytes = std::fs::read(&path)
        .unwrap_or_else(|error| panic!("build.rs embeds {path:?} into Windows launchers: {error}"));
    assert!(bytes.len() > 6, "{path:?} is too small to be an icon");
    assert_eq!(
        &bytes[0..4],
        &[0x00, 0x00, 0x01, 0x00],
        "{path:?} is not an ICO file; regenerate it with `python build/generate_icon.py`"
    );
    let image_count = u16::from_le_bytes([bytes[4], bytes[5]]);
    assert!(image_count >= 1, "{path:?} contains no icon images");
}
