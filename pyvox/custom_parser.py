from pyvox.parser import VoxParser
from pyvox.models import Vox
import numpy as np
from struct import unpack

class VoxModel(Vox):
    def __init__(self):
        super().__init__(models=[])
        self.size = None
        self.voxels = None
        self.palette = None

    def to_dense(self):
        """Convert the voxel data to a dense numpy array"""
        if self.voxels is None or self.size is None:
            return np.array([])
        return self.voxels

    @classmethod
    def from_chunks(cls, size, xyzi, rgba=None):
        # Parse size chunk
        size_x, size_y, size_z = unpack('<3I', size.content)
        
        # Parse voxel data
        n_voxels = unpack('<I', xyzi.content[:4])[0]
        voxel_data = np.frombuffer(xyzi.content[4:], dtype=np.uint8).reshape(n_voxels, 4)
        
        # Create empty voxel array
        voxels = np.zeros((size_x, size_y, size_z), dtype=np.uint8)
        
        # Fill voxel array with color indices
        for x, y, z, c in voxel_data:
            voxels[x, y, z] = c
        
        # Parse palette if available
        if rgba:
            palette = np.frombuffer(rgba.content, dtype=np.uint8).reshape(-1, 4)[:, :3]
        else:
            # Default palette
            palette = np.array([[255, 255, 255]] * 256, dtype=np.uint8)
        
        # Create model instance
        model = cls()
        model.size = (size_x, size_y, size_z)
        model.voxels = voxels
        model.palette = palette
        return model

class CustomVoxParser(VoxParser):
    class Chunk:
        def __init__(self, chunk_id, content, children):
            self.id = chunk_id
            self.content = content
            self.children = children

    def __init__(self, filename):
        self._file = open(filename, 'rb')
        super().__init__(filename)

    def _parse_chunk(self):
        """Parse a chunk from the file"""
        chunk_id = self._file.read(4)
        if not chunk_id:
            return None
            
        n_content = int.from_bytes(self._file.read(4), byteorder='little')
        n_children = int.from_bytes(self._file.read(4), byteorder='little')

        if chunk_id in [b'NOTE', b'nTRN', b'nGRP', b'nSHP']:
            # Skip node chunks and NOTE chunk data as we don't need them for visualization
            self._file.seek(n_content, 1)  # Seek relative to current position
            return None
        else:
            # Handle other chunk types
            content = self._file.read(n_content)
            children = []
            for i in range(n_children):
                child = self._parse_chunk()
                if child is not None:
                    children.append(child)
            return self.Chunk(chunk_id, content, children)

    def parse(self):
        """Parse the full VOX file"""
        if self._file.read(4) != b'VOX ':
            raise Exception('Not a VOX file')
        
        version = int.from_bytes(self._file.read(4), byteorder='little')
        if version != 150 and version != 200:
            raise Exception('Unsupported VOX version')

        self._chunks = []
        chunk = self._parse_chunk()
        while chunk:
            if chunk is not None:  # Only add non-NOTE chunks
                self._chunks.append(chunk)
            chunk = self._parse_chunk()

        self._file.close()

        main = next((c for c in self._chunks if c.id == b'MAIN'), None)
        if not main:
            raise Exception('Missing MAIN chunk')

        # Look for required chunks in MAIN's children
        size = next((c for c in main.children if c.id == b'SIZE'), None)
        if not size:
            raise Exception('Missing SIZE chunk')

        xyzi = next((c for c in main.children if c.id == b'XYZI'), None)
        if not xyzi:
            raise Exception('Missing XYZI chunk')

        rgba = next((c for c in main.children if c.id == b'RGBA'), None)

        return VoxModel.from_chunks(size, xyzi, rgba)