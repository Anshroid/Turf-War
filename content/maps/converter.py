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
spawnpoints: list[int] = []
for feature in json_data["features"]:
    if feature["geometry"]["type"] != "Polygon":
        continue
    
    json_output.append({
        "name": re.sub(r"^(\d+)", r"(\g<1>)", feature["properties"]["name"]),
        "svg_id": f"region_{i+1}",
        "default_state": min(2, ["#ff5252", "#ffd600", "#01579b", "#0f9d58"].index(feature["properties"]["fill"])),
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
    #labels text {
        font: 6px sans-serif;
        fill: #fff;
        text-anchor: middle;
        dominant-baseline: central
    }
    #labels circle {
        fill: #000a
    }
    #respawns circle, #key circle {
        fill: #0f9d58
    }
    #respawns rect, #key rect {
        fill: #fff
    }
    #key text {
        font: 6px sans-serif;
        fill: #fff;
    }

"""

defs[0].append(ElementTree.fromstring("""
<linearGradient id="RED">
    <stop stop-color="#ff5252" />
</linearGradient>"""))
defs[0].append(ElementTree.fromstring("""
<linearGradient id="RED-dark">
    <stop stop-color="#990000" />
</linearGradient>"""))
defs[0].append(ElementTree.fromstring("""
<linearGradient id="RED-locked" x1="0" x2="3" y1="0" y2="3" spreadMethod="repeat" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#ff5252" />
    <stop offset="50%" stop-color="#ff5252" />
    <stop offset="50%" stop-color="#990000" />
    <stop offset="100%" stop-color="#990000" />
</linearGradient>"""))
defs[0].append(ElementTree.fromstring("""
<linearGradient id="YELLOW">
    <stop stop-color="#ffd600" />
</linearGradient>"""))
defs[0].append(ElementTree.fromstring("""
<linearGradient id="YELLOW-dark">
    <stop stop-color="#807500" />
</linearGradient>"""))
defs[0].append(ElementTree.fromstring("""
<linearGradient id="YELLOW-locked" x1="0" x2="3" y1="0" y2="3" spreadMethod="repeat" gradientUnits="userSpaceOnUse">
    <stop offset="0%" stop-color="#ffd600" />
    <stop offset="50%" stop-color="#ffd600" />
    <stop offset="50%" stop-color="#807500" />
    <stop offset="100%" stop-color="#807500" />
</linearGradient>"""))
defs[0].append(ElementTree.fromstring("""
<linearGradient id="UNOWNED">
    <stop stop-color="#fff" />
</linearGradient>"""))

metadata = root.find("./{*}metadata")
if metadata is not None: root.remove(metadata)

regions = root.find("./{*}g[@id='figure_1']")
if regions is None: raise ValueError()
regions.set("id", "regions")
regions.set("style", "fill: #fff; stroke: #000; stroke-width: 1px;")

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

regions.append(ElementTree.Element("g", {"id": "highlight-2-container"}))
regions.append(ElementTree.Element("g", {"id": "highlight-1-container"}))

respawns = ElementTree.Element("g", id="respawns")
for i in range(1, 6):
    path_collection = regions.find(f"./{{*}}g[@id='PathCollection_{i}']")
    if path_collection is None:
        continue
    
    group = path_collection.find("./{*}g")
    if group is not None:
        del group.attrib["clip-path"]
        use = group.find("./{*}use")
        if use is not None:
            use.tag = "circle"
            del use.attrib["{http://www.w3.org/1999/xlink}href"]
            del use.attrib["style"]
            
            x = use.get("x", "")
            y = use.get("y", "")
            
            use.set("cx", x)
            use.set("cy", y)
            del use.attrib["x"]
            del use.attrib["y"]
            use.set("r", "4px")
            
            hor = ElementTree.Element("rect")
            hor.set("x", str(float(x)-2.5))
            hor.set("y", str(float(y)-0.75))
            hor.set("width", "5")
            hor.set("height", "1.5")
            hor.set("style", "fill: #fff")
            group.append(hor)
            
            vert = ElementTree.Element("rect")
            vert.set("x", str(float(x)-0.75))
            vert.set("y", str(float(y)-2.5))
            vert.set("width", "1.5")
            vert.set("height", "5")
            vert.set("style", "fill: #fff")
            group.append(vert)
        
        respawns.append(group)
    
    regions.remove(path_collection)

root.append(respawns)

i = 6
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

key_pos = (230, 220)
key = ElementTree.Element("g", id="key")

t = ElementTree.Element("text", {"x": str(key_pos[0]), "y": str(key_pos[1]-3)})
t.text = "Key:"
key.append(t)

size = 6
gap = 2
x = key_pos[0]
y = range(key_pos[1], 1000, size+gap).__iter__()
key.append(ElementTree.Element("rect", {"x": str(x), "y": str(next(y)), "width": f"{size}px", "height": f"{size}px", "style": "fill: url(#RED)"}))
key.append(ElementTree.Element("rect", {"x": str(x), "y": str(next(y)), "width": f"{size}px", "height": f"{size}px", "style": "fill: url(#YELLOW)"}))
key.append(ElementTree.Element("rect", {"x": str(x), "y": str(next(y)), "width": f"{size}px", "height": f"{size}px", "style": "fill: url(#RED-locked)"}))
key.append(ElementTree.Element("rect", {"x": str(x), "y": str(next(y)), "width": f"{size}px", "height": f"{size}px", "style": "fill: url(#YELLOW-locked)"}))
key.append(ElementTree.Element("rect", {"x": str(x), "y": str(next(y)), "width": f"{size}px", "height": f"{size}px", "style": "fill: url(#RED-dark)"}))
key.append(ElementTree.Element("rect", {"x": str(x), "y": str(next(y)), "width": f"{size}px", "height": f"{size}px", "style": "fill: url(#YELLOW-dark)"}))

cx = x+3
cy = next(y)+3
key.append(ElementTree.Element("circle", {"cx": str(cx), "cy": str(cy), "r": "3px"}))
key.append(ElementTree.Element("rect", {"x": str(cx-1.875), "y": str(cy-0.5625), "width": "3.75px", "height": "1.125px"}))
key.append(ElementTree.Element("rect", {"x": str(cx-0.5625), "y": str(cy-1.875), "width": "1.125px", "height": "3.75px"}))

y = range(key_pos[1]+size-1, 1000, size+gap).__iter__()
t = ElementTree.Element("text", {"x": str(x+size+gap), "y": str(next(y))})
t.text = "Owned by Red Team"
key.append(t)
t = ElementTree.Element("text", {"x": str(x+size+gap), "y": str(next(y))})
t.text = "Owned by Yellow Team"
key.append(t)
t = ElementTree.Element("text", {"x": str(x+size+gap), "y": str(next(y))})
t.text = "Owned by Red Team, locked"
key.append(t)
t = ElementTree.Element("text", {"x": str(x+size+gap), "y": str(next(y))})
t.text = "Owned by Yellow Team, locked"
key.append(t)
t = ElementTree.Element("text", {"x": str(x+size+gap), "y": str(next(y))})
t.text = "Red Team's home region"
key.append(t)
t = ElementTree.Element("text", {"x": str(x+size+gap), "y": str(next(y))})
t.text = "Yellow Team's home region"
key.append(t)
t = ElementTree.Element("text", {"x": str(x+size+gap), "y": str(next(y))})
t.text = "Respawn point"
key.append(t)
root.append(key)

# with open("oxford_city_centre/map.json", "w") as f:
#     json.dump(json_output, f, indent=4)

with open("oxford_city_centre/map.svg", "w") as f:
    f.write(str(ElementTree.tostring(svg_data.getroot()), "utf-8"))
