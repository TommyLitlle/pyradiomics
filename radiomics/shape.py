import numpy
import operator
import collections
from radiomics import base, imageoperations
import SimpleITK as sitk

class RadiomicsShape(base.RadiomicsFeaturesBase):

  def __init__(self, inputImage, inputMask, **kwargs):
    super(RadiomicsShape,self).__init__(inputImage,inputMask, **kwargs)

    self.pixelSpacing = inputImage.GetSpacing()
    self.cubicMMPerVoxel = reduce(lambda x,y: x*y , self.pixelSpacing)

    #self.featureNames = self.getFeatureNames()

    # Pad inputMask to prevent index-out-of-range errors
    cpif = sitk.ConstantPadImageFilter()

    padding = numpy.tile(1, 3)
    cpif.SetPadLowerBound(padding)
    cpif.SetPadUpperBound(padding)

    self.inputMask = cpif.Execute(self.inputMask)

    # Reassign self.maskArray using the now-padded self.inputMask
    self.maskArray = sitk.GetArrayFromImage(self.inputMask)

    # Volume and Surface Area are pre-calculated
    self.Volume = self.getVolumeFeatureValue()
    self.SurfaceArea = self.getSurfaceAreaFeatureValue()

    #self.InitializeFeatureVector()
    #for f in self.getFeatureNames():
    #  self.enabledFeatures[f] = True

    # TODO: add an option to instantiate the class that reuses initialization

  def getVolumeFeatureValue(self):
    """Calculate the volume of the tumor region in cubic millimeters."""
    return (self.targetVoxelArray.size * self.cubicMMPerVoxel)

  def getSurfaceAreaFeatureValue(self):
    r"""
    Calculate the surface area of the tumor region in square millimeters.

    :math:`A = \displaystyle\sum^{N}_{i=1}{\frac{1}{2}|\textbf{a}_i\textbf{b}_i x \textbf{a}_i\textbf{c}_i|}`
    """
    x, y, z = self.pixelSpacing
    xz = x*z
    yz = y*z
    xy = x*y

    surf_x = numpy.sum(numpy.abs(self.maskArray[:,:,1:] - self.maskArray[:,:,:-1])) # faces in x direction
    surf_y = numpy.sum(numpy.abs(self.maskArray[:,1:,:] - self.maskArray[:,:-1,:])) # faces in y direction
    surf_z = numpy.sum(numpy.abs(self.maskArray[1:,:,:] - self.maskArray[:-1,:,:])) # faces in z direction

    surfaceArea = surf_x * yz
    surfaceArea += surf_y * xz
    surfaceArea += surf_z * xy

    return (surfaceArea)

  def getSurfaceVolumeRatioFeatureValue(self):
    r"""
    Calculate the surface area to volume ratio of the tumor region

    :math:`surface\ to\ volume\ ratio = \frac{A}{V}`
    """
    return (self.SurfaceArea/self.Volume)

  def getCompactness1FeatureValue(self):
    r"""
    Calculate the compactness (1) of the tumor region.

    :math:`compactness\ 1 = \frac{V}{\sqrt{\pi}A^{\frac{2}{3}}}`

    Compactness 1 is a measure of how compact the shape of the tumor is
    relative to a sphere (most compact). It is a dimensionless measure,
    independent of scale and orientation. Compactness 1 is defined as the
    ratio of volume to the (surface area)^(1.5). This is a measure of the
    compactness of the shape of the image ROI
    """
    return ( (self.Volume) / ((self.SurfaceArea)**(2.0/3.0) * numpy.sqrt(numpy.pi)) )

  def getCompactness2FeatureValue(self):
    r"""
    Calculate the Compactness (2) of the tumor region.

    :math:`compactness\ 2 = 36\pi\frac{V^2}{A^3}`

    Compactness 2 is a measure of how compact the shape of the tumor is
    relative to a sphere (most compact). It is a dimensionless measure,
    independent of scale and orientation. This is a measure of the compactness
    of the shape of the image ROI.
    """
    return ((36.0 * numpy.pi) * ((self.Volume)**2.0)/((self.SurfaceArea)**3.0))

  def getMaximum3DDiameterFeatureValue(self):
    r"""
    Calculate the largest pairwise euclidean distance between tumor surface voxels.
    """
    x, y, z = self.pixelSpacing

    minBounds = numpy.array([numpy.min(self.matrixCoordinates[0]), numpy.min(self.matrixCoordinates[1]), numpy.min(self.matrixCoordinates[2])])
    maxBounds = numpy.array([numpy.max(self.matrixCoordinates[0]), numpy.max(self.matrixCoordinates[1]), numpy.max(self.matrixCoordinates[2])])

    a = numpy.array(zip(*self.matrixCoordinates))
    edgeVoxelsMinCoords = numpy.vstack([a[a[:,0]==minBounds[0]], a[a[:,1]==minBounds[1]], a[a[:,2]==minBounds[2]]]) * [z,y,x]
    edgeVoxelsMaxCoords = numpy.vstack([(a[a[:,0]==maxBounds[0]]), (a[a[:,1]==maxBounds[1]]), (a[a[:,2]==maxBounds[2]])]) * [z,y,x]

    maxDiameter = 1
    for voxel1 in edgeVoxelsMaxCoords:
      voxelDistances = numpy.sqrt(numpy.sum((edgeVoxelsMinCoords-voxel1)**2, 1))
      if voxelDistances.max() > maxDiameter:
        maxDiameter = voxelDistances.max()

    return(maxDiameter)

  def getSphericalDisproportionFeatureValue(self):
    r"""
    Calculate the Spherical Disproportion of the tumor region.

    :math:`spherical\ disproportion = \frac{A}{4\pi R^2}`

    Spherical Disproportion is the ratio of the surface area of the
    tumor region to the surface area of a sphere with the same
    volume as the tumor region.
    """
    R = ( (3.0*self.Volume)/(4.0*numpy.pi) )**(1.0/3.0)
    return ( (self.SurfaceArea)/(4.0*numpy.pi*(R**2.0)) )

  def getSphericityFeatureValue(self):
    r"""
    Calculate the Sphericity of the tumor region.

    :math:`sphericity = \frac{\pi^{\frac{1}{3}}(6V)^{\frac{2}{3}}}{A}`

    Sphericity is a measure of the roundness of the shape of the tumor region
    relative to a sphere. This is another measure of the compactness of a tumor.
    """
    return ( ((numpy.pi)**(1.0/3.0) * (6.0 * self.Volume)**(2.0/3.0)) / (self.SurfaceArea) )
