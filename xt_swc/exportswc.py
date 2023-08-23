# Export Filament
# By Sarun Gulyanon 28 July 2018
# Adapted by Christoph Sommer 31 Jannuary 2022
#
# <CustomTools>
#  <Menu>
#    <Submenu name="SWC">
#       <Item name="Export Filament as SWCs (micron)" icon="Python3">
#           <Command>Python3XT::ExportSWC_um(#i)</Command>
#       </Item>
#       <Item name="Export Filament as SWCs (pixel)" icon="Python3">
#           <Command>Python3XT::ExportSWC_px(#i)</Command>
#       </Item>
#     </Submenu>
#  </Menu>
# </CustomTools>

import traceback

try:
    import ImarisLib
    import tkinter as tk
    from tkinter import messagebox

    from tkinter.filedialog import asksaveasfilename
    import numpy as np
    import time

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


def ExportSWC_um(aImarisId):
    ExportSWC(aImarisId, False)


def ExportSWC_px(aImarisId):
    ExportSWC(aImarisId, True)


@exceptionPrinter
def ExportSWC(aImarisId, in_pixel):
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

    ####
    scene = vImaris.GetSurpassScene()

    filemnt_objs = []
    for ii in range(scene.GetNumberOfChildren()):
        child = scene.GetChild(ii)
        if vImaris.GetFactory().IsFilaments(child):
            filemnt_objs.append(vFactory.ToFilaments(child))
    ####

    if len(filemnt_objs) == 0:
        print("No filaments available in scene... aborting.")
        time.sleep(4)
        return

    # get pixel scale in XYZ resolution (pixel/um)
    V = vImaris.GetDataSet()
    pixel_scale = np.array(
        [
            V.GetSizeX() / (V.GetExtendMaxX() - V.GetExtendMinX()),
            V.GetSizeY() / (V.GetExtendMaxY() - V.GetExtendMinY()),
            V.GetSizeZ() / (V.GetExtendMaxZ() - V.GetExtendMinZ()),
        ]
    )
    pixel_offset = np.array([V.GetExtendMinX(), V.GetExtendMinY(), V.GetExtendMinZ()])
    # ad-hoc fix Z-flip when |maxZ| < |minZ|
    if abs(V.GetExtendMinZ()) > abs(V.GetExtendMaxZ()):
        pixel_offset = np.array(
            [V.GetExtendMinX(), V.GetExtendMinY(), V.GetExtendMaxZ()]
        )
        pixel_scale[2] = -pixel_scale[2]

    # get base filename
    root = tk.Tk()
    root.withdraw()
    savename = asksaveasfilename(defaultextension=".swc")
    root.destroy()
    if not savename:  # asksaveasfilename return '' if dialog closed with "cancel".
        print("No files selected")
        time.sleep(4)
        return
    print(savename)

    for k, vFilaments in enumerate(filemnt_objs):
        # go through Filaments and convert to SWC format

        vCount = vFilaments.GetNumberOfFilaments()
        for vFilamentIndex in range(vCount):
            head = 0
            vFilamentsXYZ = vFilaments.GetPositionsXYZ(vFilamentIndex)
            vFilamentsEdges = vFilaments.GetEdges(vFilamentIndex)
            vFilamentsRadius = vFilaments.GetRadii(vFilamentIndex)
            vFilamentsTypes = vFilaments.GetTypes(vFilamentIndex)

            # vFilamentsTime = vFilaments.GetTimeIndex(vFilamentIndex)

            N = len(vFilamentsXYZ)
            G = np.zeros((N, N), np.bool)
            visited = np.zeros(N, np.bool)

            for p1, p2 in vFilamentsEdges:
                G[p1, p2] = True
                G[p2, p1] = True

            # traverse through the Filament using BFS
            swc = np.zeros((N, 7))
            visited[0] = True
            queue = [0]
            prevs = [-1]
            while queue:
                cur = queue.pop()
                prev = prevs.pop()
                swc[head] = [
                    head + 1,
                    vFilamentsTypes[cur],
                    0,
                    0,
                    0,
                    vFilamentsRadius[cur],
                    prev,
                ]
                swc[head, 2:5] = vFilamentsXYZ[cur] - pixel_offset
                if in_pixel:
                    swc[head, 2:5] *= pixel_scale

                for idx in np.where(G[cur])[0]:
                    if not visited[idx]:
                        visited[idx] = True
                        queue.append(idx)
                        prevs.append(head + 1)
                head = head + 1
            # write to file

            fil_out = savename[:-4] + f"_filament_{k:03d}_id_{vFilamentIndex:02d}.swc"
            np.savetxt(fil_out, swc, "%d %d %f %f %f %f %d")
            print("Export to " + fil_out + " completed")

    tk.Tk().withdraw()
    messagebox.showinfo("Success", "SWCs have been successfully exported.")
