# Timecode font

Chakra Petch Bold is bundled locally for the teleprompter timer. No font download
or system font installation is required at runtime. Other interface controls use
the platform's Qt Quick Controls style and system font.

Source: [Google Fonts](https://github.com/google/fonts/tree/main/ofl/chakrapetch)
License: SIL Open Font License 1.1; see `ChakraPetch-OFL.txt`.

The font is loaded through a relative QML URL, and `dubbing_manager.spec` includes
this directory in both macOS and Windows packages. A system monospace fallback
keeps the timecode readable if the font asset is unavailable.
