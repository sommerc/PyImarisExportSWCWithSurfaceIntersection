#
#
#  Export filament as SWC with Surface Interection
#
#
#    <CustomTools>
#      <Menu>
#       <Item name="Export filament as SWC with Surface Interection" icon="Python3" tooltip="Export SWC with Surface Interection">
#         <Command>Python3XT::main(%i)</Command>
#       </Item>
#      </Menu>
#    </CustomTools>


try:
    # Standard library imports
    import traceback

    # GUI imports
    import tkinter as tk
    from tkinter import messagebox
    from tkinter import simpledialog

    # More imports
    import ImarisLib

    import tifffile
    import numpy as np
    import pandas as pd
    from skimage import measure, morphology
    from skimage.draw import line_nd
    from tqdm.auto import tqdm, trange

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


def GetSufaceIndices(Scene, Imaris):
    indecies = []
    for ii in range(Scene.GetNumberOfChildren()):
        child = Scene.GetChild(ii)
        if Imaris.GetFactory().IsSurfaces(child):
            indecies.append(ii)

    if len(indecies) == 0:
        print("Warning: No Surface in Scene...")
    return indecies


def getExtent(DataSet):
    """Get the X,Y,Z extents of a dataset"""
    return [
        DataSet.GetExtendMinX(),
        DataSet.GetExtendMinY(),
        DataSet.GetExtendMinZ(),
        DataSet.GetExtendMaxX(),
        DataSet.GetExtendMaxY(),
        DataSet.GetExtendMaxZ(),
    ]


def getFilament(Scene, prefix="Filament"):
    for i in range(Scene.GetNumberOfChildren()):
        if Scene.GetChild(i).GetName().startswith(prefix):
            return Scene.GetChild(i)
    raise RuntimeError("No Filament found")


def getMaskLabelImage(surface, DataSet):
    extent = getExtent(DataSet)
    m = surface.GetMask(
        *extent, DataSet.GetSizeX(), DataSet.GetSizeY(), DataSet.GetSizeZ(), 0
    )
    mask = np.array(m.GetDataShorts())[0, 0]
    label_img = measure.label(mask)

    nSurfaces = len(surface.GetIds())

    print(f"nSurfaces in Imaris={nSurfaces}, labels retrieved={label_img.max()}")

    return label_img


def askForSurfacesToProcess(Scene, Imaris):
    root = tk.Tk()

    class RunIt:
        def __init__(self):
            self.ok = False

        def run(self, ok):
            self.ok = ok
            root.destroy()

    runit = RunIt()

    vars = {}
    surface_indeces = GetSufaceIndices(Scene, Imaris)

    for i, si in enumerate(surface_indeces):
        child = Scene.GetChild(si)
        surface_name = child.GetName()
        vars[(surface_name, si)] = tk.IntVar()
        cb = tk.Checkbutton(
            root,
            text=child.GetName(),
            variable=vars[(surface_name, si)],
        )
        cb.grid(row=0, column=i)
        if surface_name.lower()[:4] in ["mito", "cd68"]:
            cb.select()

    tk.Button(
        root,
        text="Run",
        command=lambda: runit.run(True),
    ).grid(row=1, column=1)

    tk.Button(
        root,
        text="Close",
        command=lambda: runit.run(False),
    ).grid(row=1, column=0)

    root.mainloop()

    if not runit.ok:
        # User said: Cancel
        return {}

    return {k[0]: k[1] for k, v in vars.items() if v.get() > 0}


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
        block[arr_single_mask] = i + 1

    return label_img


def exportLabelImageFeatures(Imaris, DataSet, Scene, surface_dict, filename_base):
    label_img_dict = {}
    for surface_name, si in surface_dict.items():
        print(f"{surface_name}: exporting surface label img table...")
        surface = Imaris.GetFactory().ToSurfaces(Scene.GetChild(si))

        # mask = getSurfaceLabelImage(surface, V, scale=1)
        label_img = getSurfaceLabelImage(surface, DataSet)
        label_img_dict[surface_name] = label_img

        rp = measure.regionprops_table(
            label_img,
            properties=(
                "label",
                "area",
                "centroid",
                # "inertia_tensor_eigvals",
                # "equivalent_diameter_area",
                # "feret_diameter_max"
            ),
        )

        rp_tab = pd.DataFrame(rp)
        rp_tab.to_csv(f"{filename_base}_{surface_name}.tab", sep="\t", index=False)

    return label_img_dict


def exportExtendedSWC(Imaris, DataSet, Scene, label_img_dict, filename_base):
    savename = f"{filename_base}.extended.swc"
    n_surfaces = len(label_img_dict)

    extent = getExtent(DataSet)
    Filament = Imaris.GetFactory().ToFilaments(getFilament(Scene))

    pixel_scale = np.array(
        [
            (DataSet.GetSizeX()) / (DataSet.GetExtendMaxX() - DataSet.GetExtendMinX()),
            (DataSet.GetSizeY()) / (DataSet.GetExtendMaxY() - DataSet.GetExtendMinY()),
            (DataSet.GetSizeZ()) / (DataSet.GetExtendMaxZ() - DataSet.GetExtendMinZ()),
        ]
    )
    pixel_offset = np.array(extent[:3])

    # go through Filaments and convert to SWC format
    head = 0
    vCount = Filament.GetNumberOfFilaments()

    vFilamentIndex = 0
    filamentXYZ = Filament.GetPositionsXYZ(vFilamentIndex)
    filamentEdges = Filament.GetEdges(vFilamentIndex)
    filamentRadius = Filament.GetRadii(vFilamentIndex)
    filamentTypes = Filament.GetTypes(vFilamentIndex)

    N = len(filamentXYZ)
    G = np.zeros((N, N), bool)
    visited = np.zeros(N, bool)
    for p1, p2 in filamentEdges:
        G[p1, p2] = True
        G[p2, p1] = True

    # traverse through the Filament using BFS
    swc = np.zeros((N, 7 + n_surfaces), dtype=object)
    visited[0] = True
    queue = [0]
    prevs = [-1]
    last_cur = [-1]

    db_out_dict = {}
    for sn, limg in label_img_dict.items():
        db_out_dict[sn] = limg.copy()

    while queue:
        cur = queue.pop()
        prev = prevs.pop()
        l_cur = last_cur.pop()

        # write position of cur
        swc[head] = [
            head + 1,
            filamentTypes[cur],
            0,
            0,
            0,
            filamentRadius[cur],
            prev,
        ] + [-1] * n_surfaces
        pos = filamentXYZ[cur] - pixel_offset
        swc[head, 2:5] = pos * pixel_scale

        # write labels of masks overlapping with edge
        if l_cur >= 0:
            src_px = ((filamentXYZ[l_cur] - pixel_offset) * pixel_scale).astype(
                np.int32
            )
            des_px = ((filamentXYZ[cur] - pixel_offset) * pixel_scale).astype(np.int32)

            ll = line_nd(src_px, des_px, endpoint=True)

            for i, (surface_name, mask) in enumerate(label_img_dict.items()):

                a = list(set(mask[ll]) - {0})

                db_out_dict[surface_name][ll] = 100
                if len(a) > 0:
                    db_out_dict[surface_name][ll] = a[0] + 100
                    swc[head, 7 + i] = ",".join(map(str, a))

        for idx in np.where(G[cur])[0]:
            if not visited[idx]:
                visited[idx] = True
                queue.append(idx)
                prevs.append(head + 1)
                last_cur.append(cur)
        head = head + 1

    for k, v in db_out_dict.items():
        print(k)
        tifffile.imsave(
            f"{filename_base}_{k}_db.tif", v[:, None].swapaxes(0, 3), imagej=True
        )

    swc_tab = pd.DataFrame(
        swc,
        columns=["SampleID", "TypeID", "x", "y", "z", "r", "ParentID"]
        + [f"{sn}_labels" for sn in label_img_dict.keys()],
    )
    swc_tab.to_csv(savename, sep=" ", index=False)
    print("Export to " + savename + " completed")


@exceptionPrinter
def main(aImarisId):
    # Create an ImarisLib object
    Imaris, DataSet, Scene = getImaris(aImarisId)

    # User Dialog to select surfaces

    surface_dict = askForSurfacesToProcess(Scene, Imaris)

    if len(surface_dict) == 0:
        return

    # Get user selected Surfaces
    print(surface_dict)

    filename_base = Imaris.GetCurrentFileName()[:-4]

    label_img_dict = exportLabelImageFeatures(
        Imaris, DataSet, Scene, surface_dict, filename_base
    )

    exportExtendedSWC(Imaris, DataSet, Scene, label_img_dict, filename_base)

    input("Done: press Return to close!")
