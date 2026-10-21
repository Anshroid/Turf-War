from typing import Never
from xml.etree import ElementTree
import json
import re

with open("in.json", "r") as f:
    json_data = json.load(f)

ElementTree.register_namespace("", "http://www.w3.org/2000/svg")
ElementTree.register_namespace("xlink", "http://www.w3.org/1999/xlink")
with open("in.svg", "r") as f:
    svg_data = ElementTree.parse(f)

i = 0
json_output: list[dict[str, str | int | list[Never]]] = []
for feature in json_data["features"]:
    if feature["geometry"]["type"] == "Point":
        continue
    
    json_output.append({
        "name": re.sub(r"^(\d+)", r"(\g<1>)", feature["properties"]["name"]),
        "svg_id": f"region_{i+1}",
        "default_state": min(2, ["#ff5252", "#ffea00", "#757575", "#0f9d58"].index(feature["properties"]["fill"])),
        "adjacent": []
    })
    
    i += 1
    
root = svg_data.getroot()
root.set("width", root.get("width", "").replace("pt", "px"))
root.set("height", f"{float(root.get("height", "").replace("pt", "")) + 40}px")

view_box = root.get("viewBox", "").split()
view_box[3] = str(float(view_box[3]) + 40)
root.set("viewBox", " ".join(view_box))

defs = root.findall("./{*}defs")
root.remove(defs[1])
style = defs[0].find("./{*}style")
if style is not None: 
    style.text = """
    * {
        stroke-linejoin: round;
        stroke-linecap: round
    } 
    text {
        font: 6px serif;
        fill: #fff;
        text-anchor: middle;
        dominant-baseline: central
    }
"""

defs[0].append(ElementTree.fromstring("""
<linearGradient id="RED-locked" x1="0" x2="3" y1="0" y2="3" spreadMethod="repeat" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#000" />
    <stop offset="50%" stop-color="#000" />
    <stop offset="50%" stop-color="#000" />
    <stop offset="100%" stop-color="#000" />
</linearGradient>"""))
defs[0].append(ElementTree.fromstring("""
<linearGradient id="YELLOW-locked" x1="0" x2="3" y1="0" y2="3" spreadMethod="repeat" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#000" />
    <stop offset="50%" stop-color="#000" />
    <stop offset="50%" stop-color="#000" />
    <stop offset="100%" stop-color="#000" />
</linearGradient>"""))

metadata = root.find("./{*}metadata")
if metadata is not None: root.remove(metadata)

regions = root.find("./{*}g[@id='figure_1']")
if regions is None: raise ValueError()
regions.set("id", "regions")
regions.set("style", "fill: #fff; stroke: #000; stroke-width: 0.5px;")

patch_1 = regions.find("./{*}g[@id='patch_1']")
if patch_1 is not None: regions.remove(patch_1)

axes_1 = regions.find("./{*}g[@id='axes_1']")
if axes_1 is not None: 
    for child in axes_1.findall("./*"):
        regions.append(child)
    regions.remove(axes_1)

patch_2 = regions.find("./{*}g[@id='patch_2']")
if patch_2 is not None: regions.remove(patch_2)

i = 3
patch = regions.find(f"./{{*}}g[@id='patch_{i}']")
while patch is not None:
    patch.set("id", f"region_{i-2}")
    
    path = patch.find("./{*}path")
    if path is not None:
        del path.attrib["clip-path"]
        del path.attrib["style"]
    
    i += 1
    patch = regions.find(f"./{{*}}g[@id='patch_{i}']")

i = 1
path_collection = regions.find(f"./{{*}}g[@id='PathCollection_{i}']")
labels = ElementTree.Element("g", id="labels")
while path_collection is not None:
    group = path_collection.find("./{*}g")
    if group is not None:
        del group.attrib["clip-path"]
        use = group.find("./{*}use")
        if use is not None:
            use.tag = "text"
            del use.attrib["{http://www.w3.org/1999/xlink}href"]
            del use.attrib["style"]
            use.text = str(i)
            
            circle = ElementTree.Element("circle")
            circle.set("cx", use.get("x", ""))
            circle.set("cy", use.get("y", ""))
            circle.set("r", "5px")
            group.insert(0, circle)
        
        labels.append(group)
    
    regions.remove(path_collection)
    
    i += 1
    path_collection = regions.find(f"./{{*}}g[@id='PathCollection_{i}']")

root.append(labels)

root.append(ElementTree.fromstring("""
<g id="win-bar">
    <rect x="5%" y="93%" height="3%" width="90%" style="fill: #fff; stroke: #fff; stroke-width: 1.5px" />
    <rect x="5%" y="93%" height="3%" width="30%" style="fill: #000" />
    <rect x="65%" y="93%" height="3%" width="30%" style="fill: #000" />
</g>"""))

with open("out.json", "w") as f:
    json.dump(json_output, f, indent=4)

with open("out.svg", "w") as f:
    f.write(str(ElementTree.tostring(svg_data.getroot()), "utf-8"))
