{
  description = "Label printer development environment";

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
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            just
            imagemagick
            chafa  # Terminal image viewer
            python3
            python3Packages.pillow
            uv
          ];

          shellHook = ''
            echo "🖨️  Label printer development environment"
            echo "Available commands:"
            echo "  just --list"
            echo "  just print-text 'Your Text'"
            echo "  just print-text-horizontal 'Your Text'"
            echo "  just preview-text 'Your Text'"
          '';
        };
      });
}