#
#
#  Export label image of Imaris Surface
#  christophsommer23@gmail.com (2023)
#
#
#    <CustomTools>
#      <Menu>
#       <Item name="Export label image of Imaris Surface" icon="Python3" tooltip="Export label image of Imaris Surface">
#         <Command>Python3XT::main(%i)</Command>
#       </Item>
#      </Menu>
#    </CustomTools>
#

import traceback

try:
    # Standard library imports

    # GUI imports
    import tkinter as tk
    from tkinter import messagebox
    from tkinter import filedialog

    # Import ImarisLib
    import ImarisLib

    # Non standard library imports
    import tifffile
    from skimage.transform import resize
    import numpy as np
    from tqdm.auto import trange

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


def getImaris(aImarisId):
    # Create an ImarisLib object
    vImarisLib = ImarisLib.ImarisLib()

    # Get an imaris object with id aImarisId
    vImaris = vImarisLib.GetApplication(aImarisId)

    # Check if the object is valid
    if vImaris is None:
        messagebox.showwarning("Could not connect to Imaris!")
        raise RuntimeError("Could not connect to Imaris!")

    # Get the dataset
    vDataSet = vImaris.GetDataSet()
    if vDataSet is None:
        messagebox.showwarning("An image must be loaded to run this XTension!")
        RuntimeError("An image must be loaded to run this XTension!")

    scene = vImaris.GetSurpassScene()

    return vImaris, vDataSet, scene


def getSurfaceLabelImage(surface, ds):
    nSurfaces = len(surface.GetIds())

    label_img = np.zeros((ds.GetSizeX(), ds.GetSizeY(), ds.GetSizeZ()), np.uint16)

    voxel_len_x = (ds.GetExtendMaxX() - ds.GetExtendMinX()) / ds.GetSizeX()
    voxel_len_y = (ds.GetExtendMaxY() - ds.GetExtendMinY()) / ds.GetSizeY()
    voxel_len_z = (ds.GetExtendMaxZ() - ds.GetExtendMinZ()) / ds.GetSizeZ()

    for i in trange(nSurfaces):
        sl = surface.GetSurfaceDataLayout(i)

        block_start_x = int((sl.mExtendMinX - ds.GetExtendMinX()) / voxel_len_x)
        block_end_x = int((sl.mExtendMaxX - ds.GetExtendMinX()) / voxel_len_x + 1)

        block_start_y = int((sl.mExtendMinY - ds.GetExtendMinY()) / voxel_len_y)
        block_end_y = int((sl.mExtendMaxY - ds.GetExtendMinY()) / voxel_len_y + 1)

        block_start_z = int((sl.mExtendMinZ - ds.GetExtendMinZ()) / voxel_len_z)
        block_end_z = int((sl.mExtendMaxZ - ds.GetExtendMinZ()) / voxel_len_z + 1)

        block_start_x = max(0, block_start_x)
        block_start_y = max(0, block_start_y)
        block_start_z = max(0, block_start_z)

        block_end_x = min(label_img.shape[0] - 1, block_end_x)
        block_end_y = min(label_img.shape[1] - 1, block_end_y)
        block_end_z = min(label_img.shape[2] - 1, block_end_z)

        simgle_mask = surface.GetSingleMask(
            i,
            sl.mExtendMinX,
            sl.mExtendMinY,
            sl.mExtendMinZ,
            sl.mExtendMaxX,
            sl.mExtendMaxY,
            sl.mExtendMaxZ,
            block_end_x - block_start_x,
            block_end_y - block_start_y,
            block_end_z - block_start_z,
        )
        arr_single_mask = np.array(simgle_mask.GetDataShorts(), dtype=bool)[0, 0]

        block = label_img[
            block_start_x:block_end_x,
            block_start_y:block_end_y,
            block_start_z:block_end_z,
        ]

        # binary indexing here to set label id
        if block.shape != arr_single_mask.shape:
            print(
                f"Warning: shape mismatch block != mask :{block.shape} != {arr_single_mask.shap}. Resizing..."
            )
            arr_single_mask = resize(
                arr_single_mask, output_shape=block.shape, order=0
            ).astype(bool)
        block[arr_single_mask] = i + 1

    return label_img


@exceptionPrinter
def main(aImarisId):
    # Create an ImarisLib object
    Imaris, DataSet, Scene = getImaris(aImarisId)

    sel_surfaces = Imaris.GetFactory().ToSurfaces(Imaris.GetSurpassSelection())
    if sel_surfaces is None:
        messagebox.showinfo(title="Abort", message="No Surface to export selected...")
        return

    surface_name = sel_surfaces.GetName()

    root = tk.Tk()
    root.withdraw()

    label_img_fn = filedialog.asksaveasfilename(
        parent=root,
        title="Save as .tif label image",
        initialfile=f"{surface_name}.labels.tif",
        defaultextension=".tif",
        filetypes=[("tif file", ".tif")],
    )

    if len(label_img_fn) > 0:
        label_img = getSurfaceLabelImage(sel_surfaces, DataSet)
        label_img = label_img.swapaxes(0, 2)[:, None]
        print(f"Writing label image of surface {surface_name} to {label_img_fn}...")
        tifffile.imsave(label_img_fn, label_img, imagej=True)
        messagebox.showinfo(
            title="Label Image Exort",
            message=f"Label image of surface {surface_name} exported to {label_img_fn}",
        )
