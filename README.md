# 🛡️ Offline Privacy Toolkit

A single-file, 100% offline toolkit that runs from a **USB stick** in any browser — **phone or PC**.
No install, no server, no internet, no dependencies.

**Three tools in one page:**

| Tool | What it does |
|------|--------------|
| 🔍 **Metadata Viewer** | Reads hidden metadata inside images — EXIF, **GPS location**, camera make/model/serial, timestamps, XMP, IPTC, PNG text chunks — and flags the privacy-sensitive fields. |
| 🧽 **Metadata Eraser** | Strips all that metadata out. *Lossless* mode keeps the original pixels (JPEG/PNG); *Re-encode* mode redraws the image for a guaranteed-clean file of any format. Batch-capable. |
| 🔥 **Secure Shredder** | Overwrites the actual bytes of files **you pick** with multiple passes, then blanks them to 0 bytes so you can delete an empty shell. |

Everything happens in your browser's memory. Nothing is uploaded — turn on Airplane Mode and it all still works.

---

## 📦 Put it on a USB

The whole toolkit is **one file: [`index.html`](index.html)**. Copy it to the root of a USB drive.

- **Windows / macOS / Linux** — plug in, double-click `index.html`.
- **Android** — plug the USB in via OTG, open the Files app, tap `index.html` → *Open with* a browser.
- **iPhone / iPad** — use a Lightning/USB-C reader, open Files, tap the file (opens in Safari).

---

## 🔬 Honest limits (please read)

- **The viewer & eraser** work on any browser, fully offline.
- **The shredder** uses the browser **File System Access API** to overwrite files in place. That API exists on
  **Chrome / Edge (desktop & Android)**. On **iOS Safari and Firefox** it's unavailable — the page detects this
  and shows OS-level alternatives (`shred -u` on Linux, etc.) instead of pretending to work.
- **Flash media (USB sticks & SSDs) use wear-levelling**, so an in-place overwrite may be redirected to
  different physical cells, leaving old data behind in cells software can't reach. Overwriting helps, but the
  only reliable protection on flash is **full-disk / hardware encryption** (BitLocker To Go, VeraCrypt, LUKS)
  so any leftover fragments are unreadable ciphertext. On classic spinning hard drives, multi-pass overwrite
  is genuinely effective.

No warranty. For high-stakes data, combine this with full-disk encryption — and, for maximum assurance,
physical destruction of the media.

---

## 🧱 How it's built

Pure vanilla HTML/CSS/JavaScript in one file — no frameworks, no CDN, no network calls. The EXIF/TIFF, JPEG,
and PNG parsers and the lossless metadata strippers are hand-written and run entirely client-side, which is
what makes the whole thing work from a USB with no internet.
