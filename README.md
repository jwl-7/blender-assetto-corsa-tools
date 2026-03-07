# Blender KN5/KSANIM Exporter

This fork of the KN5 exporter is made to support the exporting of cars instead of tracks.

## Features

* File format version 5
* Export blender car -> kn5
* Export blender track -> kn5
* Export blender anim -> ksanim
* Import ksEditor Persistence -> settings json
* Blender mesh objects as kn5 geometry
* Blender image textures as kn5 textures
* Set material and object settings with JSON
* Texture mapping with UV maps or flat mapping
* Multiple materials per object
* Bundle texture folder

## Technical

* Automatically search for textures defined in `settings.json`, even when they are not bound to the node in blender
* Hardcoded texture slots to ensure proper mapping
* Tangent space calculations ensures cars have proper reflections
* Bounding sphere calculation updated for cars

## Requirements

* Blender 3.0+

## Install

1. Download the `blender_assetto_corsa_tools.zip` from the [latest Release](https://github.com/jwl-7/blender-assetto-corsa-tools/releases/latest).
2. Start Blender
3. Go to `Edit` > `Preferences` > `Add-ons`
4. Click `Install...` and select the downloaded zip file
5. Enable the `Assetto Corsa (.kn5) (.ks)` addon

## Usage

### Cars / Tracks
1. Open up `ksEditor`
2. Go to `File` > `Open FBX` and load car FBX
3. Go to `File` > `Save Persistence` (generates `fbx.ini`)
4. Close `ksEditor`
5. Open `Blender`
6. Go to `File` > `Import` > `Assetto Corsa Persistence (fbx.ini) -> Settings (.json)` and select generated `fbx.ini`
7. Ensure the following are in the same folder where the `KN5` will be exported:
  - `settings.json`
  - `/texture` folder
8. Go to `File` > `Export` > `Assetto Corsa 3D (.kn5)`

### Animations
1. Import `.fbx`
2. Create a root bone on the armature (ex: `acroot`)
3. Go to `File` > `Export` > `Assetto Corsa Animation (.ksanim)`

## Credits

- Thomas Hagnhofer: [KN5 Exporter](https://site.hagn.io/assettocorsa/blender-kn5-exporter)
- N Murdoch: [KSANIM Exporter](https://www.overtake.gg/downloads/blender-ksanim-knh-exporter.30388/)
- Paul Greveson: [AC Tools](https://github.com/moppius/blender-assetto-corsa-tools)
