# PyImarisExportSWCWithSurfaceIntersection
Imaris Python Extension to export extended SWC files from Imaris filaments. The output SWC file contains an additional column with label IDs linking to Imaris Surfaces. Features of Imaris Surfaces are exported in seperat tab-separated files.

**Work in progress...**

## Installation
1. Setup Imaris Python 3.7 extensions 
2. Place `export_swc_with_suface_intersection.py` to your Imaris Python 3.7 library folder

## Usage

1. Open Imaris dataset containing surfaces and a filament annotation
2. Choose `Image Processing -> Export filament as SWC with Surface Interection`
3. Select Surfaces to export

For a image with name *my-image*.ims containing and selected surface called *my-surface* the following output will be created:

1. *my-image*.extended.swc`
2. *my-image*_*my-surface*.tab

The .extended.swc contains extra columns for each surface linking to label IDs. Features of Surfaces with their corresponding Label ID are stored in the .tab file.




## Ackknowedgement
SWC export code is adapted from [PyImarisSWC](https://imaris.oxinst.com/open/view/pyimarisswc) by Sarun Gulyanon