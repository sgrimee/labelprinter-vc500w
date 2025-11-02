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
        
        labelprinter = pkgs.python3Packages.buildPythonApplication {
          pname = "labelprinter";
          version = "0.1.0";
          
          src = ./.;
          format = "pyproject";
          
          nativeBuildInputs = with pkgs.python3Packages; [
            setuptools
            wheel
          ];
          
          propagatedBuildInputs = with pkgs.python3Packages; [
            pillow
          ];
          
          # Don't check for tests during build (tests require hardware)
          doCheck = false;
          
          meta = with pkgs.lib; {
            description = "Brother VC-500W label printer control - print text labels and images";
            license = licenses.agpl3Plus;
            maintainers = [ ];
            platforms = platforms.unix;
          };
        };
      in
      {
        packages = {
          default = labelprinter;
          labelprinter = labelprinter;
        };
        
        apps = {
          default = {
            type = "app";
            program = "${labelprinter}/bin/label-text";
          };
          label-text = {
            type = "app";
            program = "${labelprinter}/bin/label-text";
          };
          label-raw = {
            type = "app";
            program = "${labelprinter}/bin/label-raw";
          };
        };
        
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            just
            chafa  # Terminal image viewer
            python3
            python3Packages.pillow
            python3Packages.black
            python3Packages.flake8
            python3Packages.pytest
            uv
          ];

          shellHook = ''
            echo "🖨️  Label printer development environment"
            echo ""
            echo "Development commands:"
            echo "  just --list              - Show all available commands"
            echo "  just print-text 'Text'   - Print text label"
            echo "  just preview-text 'Text' - Preview without printing"
            echo ""
            echo "Nix commands:"
            echo "  nix run                  - Run label-text command"
            echo "  nix run .#label-text     - Run label-text command"
            echo "  nix run .#label-raw      - Run label-raw command"
            echo "  nix build                - Build the package"
            echo ""
            echo "Installation:"
            echo "  nix profile install .    - Install to user profile"
            echo "  uv tool install .        - Install with uv tool"
          '';
        };
      });
}