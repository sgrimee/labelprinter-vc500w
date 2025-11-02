# Installation Guide

## Quick Install

### Using uv tool (Fastest)

```bash
uv tool install .
```

Now use `label-text` and `label-raw` commands from anywhere!

### Using Nix

```bash
# Try it without installing
nix run . -- "Hello World"

# Install to user profile
nix profile install .

# Or add to your system flake (see README.md)
```

## System Integration

### NixOS

Add to your `flake.nix`:

```nix
{
  inputs = {
    labelprinter.url = "github:yourusername/labelprinter-vc500w";
  };

  outputs = { nixpkgs, labelprinter, ... }: {
    nixosConfigurations.yourhostname = nixpkgs.lib.nixosSystem {
      modules = [{
        environment.systemPackages = [
          labelprinter.packages.x86_64-linux.default
        ];
      }];
    };
  };
}
```

### Home Manager

```nix
{
  inputs = {
    labelprinter.url = "github:yourusername/labelprinter-vc500w";
  };

  outputs = { home-manager, labelprinter, ... }: {
    homeConfigurations.username = home-manager.lib.homeManagerConfiguration {
      modules = [{
        home.packages = [
          labelprinter.packages.x86_64-linux.default
        ];
      }];
    };
  };
}
```

### macOS (nix-darwin)

```nix
{
  inputs = {
    labelprinter.url = "github:yourusername/labelprinter-vc500w";
  };

  outputs = { darwin, labelprinter, ... }: {
    darwinConfigurations.hostname = darwin.lib.darwinSystem {
      system = "aarch64-darwin";  # or x86_64-darwin
      modules = [{
        environment.systemPackages = [
          labelprinter.packages.aarch64-darwin.default
        ];
      }];
    };
  };
}
```

## Configuration

Create `~/.config/labelprinter/config.json`:

```json
{
  "host": "VC-500W4188.local",
  "label_width_mm": 25,
  "font_size": 104,
  "font": "/path/to/font.ttf",
  "pixels_per_mm": 12.48,
  "rotate": 0
}
```

Or run the auto-detection:

```bash
just setup-printer
```

## Usage

```bash
# Print text
label-text "Hello World"

# Preview first
label-text "Test" --dry-run --preview

# Send custom image
label-raw --host VC-500W.local --print-jpeg image.jpg

# Check status
label-raw --host VC-500W.local --get-status
```

See README.md for full documentation.
