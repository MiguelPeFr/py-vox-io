# py-vox-io

> [!IMPORTANT]
> Now works with current voxel formats of version 200 and more complex models.

A Python parser and writer for the [Magica Voxel .vox
format](https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox.txt)

![sample1](https://raw.githubusercontent.com/gromgull/py-vox-io/master/samples/1.png)


The base parser/writer has no dependencies.

The VOX model class has methods to convert to/from numpy arrays, these
require numpy (duh) and pillow for image quantisation.
