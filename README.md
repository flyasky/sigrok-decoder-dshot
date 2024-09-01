# sigrok-decoder-dshot

## Notes & ToDo
The current working branch is `feature/add-telemetry-refactor`.

Temporarily disabled `raise ...` statements.

Specifically for AM32 telemetry response bitrate calculated as 23/20 instead of 5/4 (has to be the setting soon).


## Usage

### Install the latest Python to PulseView/sigrok-cli (on Windows)

Some code has been written with `match-case` instructions. So you need Python 3.10+ instead of bundled 3.4.

Download Python 3.12 embedded package, i.e. `Windows embeddable package (64-bit)`.

Replace old python related files in the PulseView installation directory with new ones. 

Create symlink to `python312.dll` named `python34.dll`.

### Debian

```
mkdir ~/.local/share/libsigrokdecode/decoders/dshot
cd ~/.local/share/libsigrokdecode/decoders/dshot
```

Then clone this repository

Reload sigrok-cli/pulseview
