# Instructions for converting a Google MyMaps map for the bot

1. Download the `.kml`s for the regions and the bot labels from the Google MyMaps
2. Import them into https://geojson.io/ and export the GeoJSON. Save this file as `in.json`.
3. Convert that to an SVG using [this converter](https://mygeodata.cloud/converter/geojson-to-svg) with the WGS84/Pseudo-Mercator system. Save this file as `in.svg`.
4. Run `converter.py`. These should be the final files.