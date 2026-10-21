# Instructions for converting a .kmz to the format used here

1. Download the .kmz from the Google MyMaps
2. Convert it to a GeoJSON file using https://geojson.io/. Save this file as `in.json`.
3. Convert that to an SVG using [this converter](https://mygeodata.cloud/converter/geojson-to-svg) with the WGS84/Pseudo-Mercator system. Save this file as `in.svg`.
4. Remove elements from the SVG:
    - Remove the `<metadata />` section
    - Remove `patch_1` and `patch_2`, and pop all elements out of `axes_1`
    - Remove the `<clipPath />` at the bottom and all references to it.
    - Remove all individual `style="fill: #ffffff"` attributes.
5. Add elements to the SVG:    
    - Add `style="fill: #ffffff"` to `figure_1`
    - Add in the `<linearGradient />` defs from the old SVG
    - Add in the `highlight-n-container`s from the old SVG
    - Add in the `win-bar` from the old SVG and increase the `height` and `viewBox`
6. Edit the SVG:
    - Change `pt` to `px` in the `height` and `width` attributes.
    - Change `stroke-linecap: butt` to `stroke-linecap: round` in the `<style />` tag.