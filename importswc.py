# Import Filament
# By Sarun Gulyanon 28 July 2018
# Adapted by Christoph Sommer 31 Jannuary 2022
#
# <CustomTools>
#  <Menu>
#    <Item name="Import SWC as FilamentSSSS" icon="Python3">
#      <Command>Python3XT::ImportSWC(#i)</Command>
#    </Item>
#  </Menu>
# </CustomTools>



try:
    import ImarisLib
    import tkinter
    from tkinter.filedialog import askopenfilenames
    import numpy as np
    import time
    import traceback

except:
    input()
    
def ImportSWC(aImarisId):
    try:
        # Create an ImarisLib object    
        vImarisLib = ImarisLib.ImarisLib()
        # Get an imaris object with id aImarisId
        vImaris = vImarisLib.GetApplication(aImarisId)
        # Check if the object is valid
        if vImaris is None:
            print('Could not connect to Imaris!')
            time.sleep(2)
            return
        
        vFactory = vImaris.GetFactory()
        vFilaments = vFactory.ToFilaments(vImaris.GetSurpassSelection())
        
        # get swc file to load
        root = tkinter.Tk()
        root.withdraw()
        swcnames = askopenfilenames(title = "Select SWC file", filetypes = (("SWC files","*.swc"),("all files","*.*")))
        root.destroy()
        
        for swcname in swcnames:
            if not swcname: # asksaveasfilename return '' if dialog closed with "cancel".
                print('No file was selected.')
                time.sleep(2)
                return
            swc = np.loadtxt(swcname)
            
            # get pixel scale in XYZ resolution (pixel/um)
            V = vImaris.GetDataSet()
            pixel_scale = np.array([V.GetSizeX() / (V.GetExtendMaxX() - V.GetExtendMinX()), \
                                    V.GetSizeY() / (V.GetExtendMaxY() - V.GetExtendMinY()), \
                                    V.GetSizeZ() / (V.GetExtendMaxZ() - V.GetExtendMinZ())])
            pixel_offset = np.array([V.GetExtendMinX(), V.GetExtendMinY(), V.GetExtendMinZ()])
            # ad-hoc fix Z-flip when |maxZ| < |minZ|
            if abs(V.GetExtendMinZ()) > abs(V.GetExtendMaxZ()):
                pixel_offset = np.array([V.GetExtendMinX(), V.GetExtendMinY(), V.GetExtendMaxZ()])
                pixel_scale[2] = -pixel_scale[2]
                
            # draw Filament
            N = swc.shape[0]
            vFilaments = vImaris.GetFactory().CreateFilaments();
            vPositions = swc[:,2:5].astype(np.float) / pixel_scale
            vPositions = vPositions + pixel_offset
            vRadii     = swc[:,5].astype(np.float)
            vTypes     = swc[:,1] #(0: Dendrite; 1: Spine)
            vEdges     = swc[:,[6, 0]]
            idx        = np.all(vEdges > 0, axis=1)
            vEdges     = vEdges[idx,:] - 1
            vTimeIndex = 0;
            vFilaments.AddFilament(vPositions.tolist(), vRadii.tolist(), vTypes.tolist(), vEdges.tolist(), vTimeIndex)
            vFilamentIndex = 0;
            vVertexIndex = 1;
            vFilaments.SetBeginningVertexIndex(vFilamentIndex, vVertexIndex)
            # Add the filament object to the scene
            vScene = vImaris.GetSurpassScene();
            vScene.AddChild(vFilaments, -1)
            print('Import ' + swcname + ' completed')
    except:
        print(traceback.format_exc())
        input()
    
        
        
        
    
    