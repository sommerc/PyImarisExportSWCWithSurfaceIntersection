# Import Filament
# By Sarun Gulyanon 28 July 2018
# Adapted by Christoph Sommer 31 Jannuary 2022
#
# <CustomTools>
#  <Menu>
#    <Submenu name="SWC">
#       <Item name="Import SWCs as Filaments (micron)" icon="Python3">
#           <Command>Python3XT::ImportSWC_um(#i)</Command>
#       </Item>
#       <Item name="Import SWCs as Filaments (pixel)" icon="Python3">
#           <Command>Python3XT::ImportSWC_px(#i)</Command>
#       </Item>
#     </Submenu>
#  </Menu>
# </CustomTools>


import traceback

try:
    import ImarisLib
    import tkinter as tk
    from tkinter import messagebox

    from tkinter.filedialog import askopenfilenames
    import numpy as np
    import time
    import traceback

except:
    print(traceback.format_exc())
    input()


def exceptionPrinter(do_stuff):
    def tmp(*args, **kwargs):
        try:
            do_stuff(*args, **kwargs)
        except Exception:
            print(traceback.format_exc())
            input("Error: hit Return to close...")

    return tmp


def ImportSWC_um(aImarisId):
    ImportSWC(aImarisId, False)


def ImportSWC_px(aImarisId):
    ImportSWC(aImarisId, True)


@exceptionPrinter
def ImportSWC(aImarisId, in_pixel):
    # Create an ImarisLib object
    vImarisLib = ImarisLib.ImarisLib()
    # Get an imaris object with id aImarisId
    vImaris = vImarisLib.GetApplication(aImarisId)
    # Check if the object is valid
    if vImaris is None:
        print("Could not connect to Imaris!")
        time.sleep(2)
        return

    vFactory = vImaris.GetFactory()
    vFilaments = vFactory.ToFilaments(vImaris.GetSurpassSelection())

    # get swc file to load
    root = tk.Tk()
    root.withdraw()
    swcnames = askopenfilenames(
        title="Select SWC file(s)",
        filetypes=(("SWC files", "*.swc"), ("all files", "*.*")),
    )
    root.destroy()

    for swcname in swcnames:
        if not swcname:  # asksaveasfilename return '' if dialog closed with "cancel".
            print("No file was selected.")
            time.sleep(2)
            return
        try:
            # standard SWC without header and 7 columns
            swc = np.loadtxt(swcname)
        except ValueError:
            try:
                # own extended format. Ommit header and extra columns
                swc = np.loadtxt(swcname, skiprows=1, usecols=range(7))
            except:
                tk.Tk().withdraw()
                messagebox.showwarning(
                    "Error",
                    "SWC format not understood...",
                )
                raise RuntimeError(f"SWC format of file '{swcname}' not understood...")

        # get pixel scale in XYZ resolution (pixel/um)
        V = vImaris.GetDataSet()
        pixel_scale = np.array(
            [
                V.GetSizeX() / (V.GetExtendMaxX() - V.GetExtendMinX()),
                V.GetSizeY() / (V.GetExtendMaxY() - V.GetExtendMinY()),
                V.GetSizeZ() / (V.GetExtendMaxZ() - V.GetExtendMinZ()),
            ]
        )
        pixel_offset = np.array(
            [V.GetExtendMinX(), V.GetExtendMinY(), V.GetExtendMinZ()]
        )
        # ad-hoc fix Z-flip when |maxZ| < |minZ|
        if abs(V.GetExtendMinZ()) > abs(V.GetExtendMaxZ()):
            pixel_offset = np.array(
                [V.GetExtendMinX(), V.GetExtendMinY(), V.GetExtendMaxZ()]
            )
            pixel_scale[2] = -pixel_scale[2]
            print("???")

        # draw Filament
        N = swc.shape[0]
        vFilaments = vImaris.GetFactory().CreateFilaments()
        pos = swc[:, 2:5].astype(np.float)
        if in_pixel:
            pos /= pixel_scale
        vPositions = pos
        vPositions = vPositions + pixel_offset
        vRadii = swc[:, 5].astype(np.float)
        vTypes = swc[:, 1]  # (0: Dendrite; 1: Spine)
        vEdges = swc[:, [6, 0]]
        idx = np.all(vEdges > 0, axis=1)
        vEdges = vEdges[idx, :] - 1
        vTimeIndex = 0
        vFilaments.AddFilament(
            vPositions.tolist(),
            vRadii.tolist(),
            vTypes.tolist(),
            vEdges.tolist(),
            vTimeIndex,
        )
        vFilamentIndex = 0
        vVertexIndex = 1
        vFilaments.SetBeginningVertexIndex(vFilamentIndex, vVertexIndex)
        # Add the filament object to the scene
        vScene = vImaris.GetSurpassScene()
        vScene.AddChild(vFilaments, -1)
        print("Import " + swcname + " completed")
