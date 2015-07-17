#    This file is part of Korman.
#
#    Korman is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Korman is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Korman.  If not, see <http://www.gnu.org/licenses/>.

import bgl

# BGL doesn't know about this as of Blender 2.74
bgl.GL_GENERATE_MIPMAP = 0x8191
bgl.GL_BGRA = 0x80E1

class GLTexture:
    def __init__(self, blimg):
        self._ownit = (blimg.bindcode == 0)
        if self._ownit:
            if blimg.gl_load() != 0:
                raise explosions.GLLoadError(blimg)
        self._blimg = blimg

    def __del__(self):
        if self._ownit:
            self._blimg.gl_free()

    def __enter__(self):
        """Sets the Blender Image as the active OpenGL texture"""
        self._previous_texture = self._get_integer(bgl.GL_TEXTURE_BINDING_2D)
        self._changed_state = (self._previous_texture != self._blimg.bindcode)
        if self._changed_state:
            bgl.glBindTexture(bgl.GL_TEXTURE_2D, self._blimg.bindcode)
        return self

    def __exit__(self, type, value, traceback):
        mipmap_state = getattr(self, "_mipmap_state", None)
        if mipmap_state is not None:
            bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_GENERATE_MIPMAP, mipmap_state)

        if self._changed_state:
            bgl.glBindTexture(bgl.GL_TEXTURE_2D, self._previous_texture)

    def generate_mipmap(self):
        """Generates all mip levels for this texture"""
        self._mipmap_state = self._get_tex_param(bgl.GL_GENERATE_MIPMAP)

        # Note that this is a very old feature from OpenGL 1.x -- it's new enough that Windows (and
        # Blender apparently) don't support it natively and yet old enough that it was thrown away
        # in OpenGL 3.0. The new way is glGenerateMipmap, but Blender likes oldgl, so we don't have that
        # function available to us in BGL. I don't want to deal with loading the GL dll in ctypes on
        # many platforms right now (or context headaches). If someone wants to fix this, be my guest!
        # It will simplify our state tracking a bit.
        bgl.glTexParameteri(bgl.GL_TEXTURE_2D, bgl.GL_GENERATE_MIPMAP, 1)

    def get_level_data(self, level=0, calc_alpha=False, bgra=False, quiet=False):
        """Gets the uncompressed pixel data for a requested mip level, optionally calculating the alpha
           channel from the image color data
        """
        width = self._get_tex_param(bgl.GL_TEXTURE_WIDTH, level)
        height = self._get_tex_param(bgl.GL_TEXTURE_HEIGHT, level)
        if not quiet:
            print("        Level #{}: {}x{}".format(level, width, height))

        # Grab the image data
        size = width * height * 4
        buf = bgl.Buffer(bgl.GL_BYTE, size)
        fmt = bgl.GL_BGRA if bgra else bgl.GL_RGBA
        bgl.glGetTexImage(bgl.GL_TEXTURE_2D, level, fmt, bgl.GL_UNSIGNED_BYTE, buf);

        # Calculate le alphas
        # NOTE: the variable names are correct for GL_RGBA. We'll still get the right values for
        # BGRA, obviously, but red will suddenly be... blue. Yeah.
        if calc_alpha:
            for i in range(0, size, 4):
                r, g, b = buf[i:i+3]
                buf[i+3] = int((r + g + b) / 3)
        return bytes(buf)

    def _get_integer(self, arg):
        buf = bgl.Buffer(bgl.GL_INT, 1)
        bgl.glGetIntegerv(arg, buf)
        return int(buf[0])

    def _get_tex_param(self, param, level=None):
        buf = bgl.Buffer(bgl.GL_INT, 1)
        if level is None:
            bgl.glGetTexParameteriv(bgl.GL_TEXTURE_2D, param, buf)
        else:
            bgl.glGetTexLevelParameteriv(bgl.GL_TEXTURE_2D, level, param, buf)
        return int(buf[0])

    @property
    def has_alpha(self):
        data = self.get_level_data(quiet=True)
        for i in range(3, len(data), 4):
            if data[i] != 255:
                return True
        return False
