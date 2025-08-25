class QuadKeyUrl(str):
    def format(self, *args, **kwargs):
        x = kwargs.pop('x', 0)
        y = kwargs.pop('y', 0)
        z = kwargs.pop('z', 0)
        kwargs.setdefault('key', self.tile_to_quadkey(x,y,z))
        return super().format(self,*args, **kwargs)

    @classmethod
    def from_url(cls, url: str):
        if '{key}' in url:
            return cls(url)
        return url

    @staticmethod
    def tile_to_quadkey(x, y, z):
        quadkey = ''
        for i in range(z, 0, -1):
            digit = 0
            mask = 1 << (i - 1)
            if (x & mask) != 0:
                digit += 1
            if (y & mask) != 0:
                digit += 2
            quadkey += str(digit)
        return quadkey
