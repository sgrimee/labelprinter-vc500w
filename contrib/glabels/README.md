# gLabels templates

`brother-vc500w-templates.xml` contains one template per cassette width
(9, 12, 19, 25 and 50 mm, i.e. CZ-1001 … CZ-1005) in a few common lengths.

```sh
mkdir -p ~/.config/libglabels/templates
cp contrib/glabels/brother-vc500w-templates.xml ~/.config/libglabels/templates/
```

Then in gLabels: *New* → search for "VC-500W". Width is the tape width,
height the label length; choose the rotated orientation for text that runs
along the tape. Need another length? Copy a `<Template>` block and change
`part`, `height` and the `Label-rectangle` height.

Print through a [`vc500w` CUPS queue](../cups/README.md) to get vivid
colours and the cut modes. The backend rotates and checks the page against
the inserted cassette.
