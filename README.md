# Blender KN5 Exporter

This fork of the KN5 exporter is made to support the exporting of cars instead of tracks.

## Features

* File format version 5
* Export blender car -> kn5
* Blender mesh objects as kn5 geometry
* Blender image textures as kn5 textures
* Set material and object settings with JSON
* Texture mapping with UV maps or flat mapping
* Multiple materials per object
* Bundle texture folder
* Utility converter for converting persistence ini -> settings file

## Technical

* Automatically search for textures defined in `settings.json`, even when they are not bound to the node in blender
* Utility converter reads and converts persistence `fbx.ini` -> `settings.json`
* Hardcoded texture slots to ensure proper mapping
* Tangent space calculations ensures cars have proper reflections
* Bounding sphere calculation updated for cars

## Requirements

* Blender 3.0+

## Install

1. Download the _assetto_corsa_tools.zip_ from the [latest Release](https://github.com/moppius/blender-assetto-corsa-tools/releases/latest).
2. Start Blender
3. Go to _Edit -> Preferences -> Addons_
4. Click "Install..." in the top right and browse to the downloaded zip file
5. Enable the **"Assetto Corsa (.kn5)"** addon

## Usage

1. Create `settings.json` file with [utility converter](./utils/fbx_ini_to_settings_json.py)
2. Make sure `settings.json` and the `/texture` folder are in the same directory that the `kn5` will be exported
3. Open Blender
3. Go to _File -> Export -> Assetto Corsa (.kn5)_
4. Select directory with generated `settings.json` and export

## Notes

This repository was initially created from the Blender 2.76 addon distributed as [_kn5exporter.zip_ on Thomas Hagnhofer's website](https://site.hagn.io/assettocorsa/blender-kn5-exporter).
