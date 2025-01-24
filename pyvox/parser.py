from struct import unpack_from as unpack, calcsize
import logging

from .models import Vox, Size, Voxel, Color, Model, Material

log = logging.getLogger(__name__)

class ParsingException(Exception): pass

def bit(val, offset):
    mask = 1 << offset
    return(val & mask)

class Chunk(object):
    def __init__(self, id, content=None, chunks=None):
        self.id = id
        self.content = content or b''
        self.chunks = chunks or []

        if id == b'MAIN':
            if len(self.content): raise ParsingException('Non-empty content for main chunk')
        elif id == b'PACK':
            self.models = unpack('i', content)[0]
        elif id == b'SIZE':
            self.size = Size(*unpack('iii', content))
        elif id == b'XYZI':
            n = unpack('i', content)[0]
            log.debug('xyzi block with %d voxels (len %d)', n, len(content))
            self.voxels = []
            self.voxels = [ Voxel(*unpack('BBBB', content, 4+4*i)) for i in range(n) ]
        elif id == b'RGBA':
            self.palette = [ Color(*unpack('BBBB', content, 4*i)) for i in range(255) ]
            # Docs say:  color [0-254] are mapped to palette index [1-255]
            # hmm
            # self.palette = [ Color(0,0,0,0) ] + [ Color(*unpack('BBBB', content, 4*i)) for i in range(255) ]
        elif id == b'MATT':
            _id, _type, weight, flags = unpack('iifi', content)
            props = {}
            offset = 16
            for b,field in [ (0, 'plastic'),
                             (1, 'roughness'),
                             (2, 'specular'),
                             (3, 'IOR'),
                             (4, 'attenuation'),
                             (5, 'power'),
                             (6, 'glow'),
                             (7, 'isTotalPower') ]:
                if bit(flags, b) and b<7: # no value for 7 / isTotalPower
                    props[field] = unpack('f', content, offset)
                    offset += 4

            self.material = Material(_id, _type, weight, props)

        else:
            raise ParsingException('Unknown chunk type: %s'%self.id)

class VoxParser(object):

    def __init__(self, filename):
        with open(filename, 'rb') as f:
            self.content = f.read()

        self.offset = 0

    def unpack(self, fmt):
        r = unpack(fmt, self.content, self.offset)
        self.offset += calcsize(fmt)
        return r

    def _parseChunk(self):

        _id, N, M = self.unpack('4sii')

        log.debug("Found chunk id %s / len %s / children %s", _id, N, M)

        content = self.unpack('%ds'%N)[0]

        start = self.offset
        chunks = [ ]
        while self.offset<start+M:
            chunks.append(self._parseChunk())

        return Chunk(_id, content, chunks)

    def parse(self):

            header, version = self.unpack('4si')

            if header != b'VOX ': raise ParsingException("This doesn't look like a vox file to me")

            if version > 200: raise ParsingException("Unknown vox version: %s expected 200 or lower"%version)

            main = self._parseChunk()

            if main.id != b'MAIN': raise ParsingException("Missing MAIN Chunk")

            chunks = list(reversed(main.chunks))
            models = 1
            palette = None
            size_chunks = []
            xyzi_chunks = []
            
            # First pass: categorize chunks
            for chunk in chunks:
                if chunk.id == b'PACK':
                    models = chunk.models
                elif chunk.id == b'RGBA':
                    palette = chunk.palette
                elif chunk.id == b'SIZE':
                    size_chunks.append(chunk)
                elif chunk.id == b'XYZI':
                    xyzi_chunks.append(chunk)
            
            log.debug("file has %d models", models)
            
            # Ensure we have matching pairs of SIZE and XYZI chunks
            if len(size_chunks) != len(xyzi_chunks):
                raise ParsingException(f"Mismatched number of SIZE ({len(size_chunks)}) and XYZI ({len(xyzi_chunks)}) chunks")
            
            # Create models from matching pairs
            models = [self._parseModel(size, xyzi) for size, xyzi in zip(size_chunks, xyzi_chunks)]

            # Filter out chunks that have material information
            materials = [c.material for c in chunks if hasattr(c, 'material')]

            return Vox(models, palette, materials)



    def _parseModel(self, size, xyzi):
        if size.id != b'SIZE': raise ParsingException('Expected SIZE chunk, got %s', size.id)
        if xyzi.id != b'XYZI': raise ParsingException('Expected XYZI chunk, got %s', xyzi.id)

        return Model(size.size, xyzi.voxels)




if __name__ == '__main__':

    import sys
    import coloredlogs

    coloredlogs.install(level=logging.DEBUG)


    VoxParser(sys.argv[1]).parse()
