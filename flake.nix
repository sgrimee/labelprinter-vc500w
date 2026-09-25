{
  description = "Brother VC-500W label printer control";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};



      in
       {
         packages = { };

         apps = { };
        
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            mise
            chafa  # Terminal image viewer
            python311
            uv
            # Build dependencies for pycups
            cups
            gcc
          ];

          shellHook = ''
            echo "🖨️  Label printer development environment (Python 3.11)"
            echo ""
            echo "Development commands:"
            echo "  mise tasks                         - Show all available tasks"
            echo "  mise run print-text-direct 'Text' - Print text label"
            echo "  mise run preview-text 'Text'      - Preview without printing"
            echo ""
            echo "Python commands:"
            echo "  uv run python -m labelprinter.print_text 'Text'  - Print text label"
            echo "  uv run python -m labelprinter                      - Run main module"
            echo ""
            echo "Dependencies:"
            echo "  uv sync                 - Install Python dependencies"
            echo "  uv sync --all-extras    - Install with CUPS support"
            echo ""
            echo "Installation:"
            echo "  uv tool install .        - Install with uv tool"
            echo ""
            echo "Note: Uses Python 3.11 for pycups compatibility"
          '';
        };
      });
}