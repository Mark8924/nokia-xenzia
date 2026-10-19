"""DCT4 format decoding, adapted from sp00nznet/nokia-recomp (MIT).
See third_party/nokia-recomp-LICENSE. No firmware data is included.
"""
MBIT = [0x1221,0xa91a,0x52a5,0x0908, 0xa918,0x1020,0xffff,0x52a1,
        0x0100,0x1220,0xad1a,0x0900, 0x1000,0x2908,0x5221,0xa908]
MADDR = [0x0fae,0x3e7f,0xc99f,0xd6f7, 0xa71b,0x14c4,0x52a5,0xcbb1,
         0x4285,0xefdf,0xdff7,0x5080, 0xee9f,0x0000,0x8432,0x5221,
         0x4084,0xa91a,0x56e7,0xb93a, 0x5b21,0xa818,0x0000,0xefdf]
MADDR_ADJ = [(0x00140,0x1000),(0x00220,0x52a1),(0x00480,0x1221),(0x00600,0xb928),
             (0x00810,0x5221),(0x00840,0x1220),(0x00900,0x2008),(0x01020,0x1221),
             (0x01080,0x0908),(0x01100,0x52a1),(0x02020,0x0100),(0x02080,0xfbbd),
             (0x04010,0xa91a),(0x04040,0xa908),(0x08008,0x2908),(0x09000,0x1000),
             (0x0a000,0xbd3a),(0x10010,0xad1a),(0x10040,0x5221),(0x10400,0x0908),
             (0x20200,0x53a5),(0x40040,0xa91a),(0x44000,0x1b20),(0x80100,0xa918),
             (0x800000,0xb908)]
TYPE_MCU, TYPE_PPM = 0, 1
FLASH_START = 0x1000000     # MCU flash base; PPM images start above this
CRYPT_START = 0x84          # first 0x84 bytes are the plaintext header
AUTO_OFFSET, AUTO_VALUE = 0x84, 0xffff   # MCU CryptKey auto-detect

EN = [0]*65536; DE = [0]*65536
for _c in range(65536):
    _nc = 0
    for _i in range(16):
        if _c & (1 << _i): _nc ^= MBIT[_i]
    DE[_nc] = _c; EN[_c] = _nc

def _address_bits(code, addr):
    addr &= 0xffffffff
    for bits, xorv in MADDR_ADJ:
        if (addr & bits) == bits: code ^= xorv
    for i in range(24):
        if addr & (1 << (i+1)): code ^= MADDR[i]
    return code & 0xffff

def _get(buf, o): return ((buf[o] << 8) | buf[o ^ 1]) & 0xffff
def _set(buf, o, code): buf[o] = (code >> 8) & 0xff; buf[o ^ 1] = code & 0xff


def decode_region(data, base, offset, length, key):
    if offset % 2 or length % 2 or offset < 0 or offset + length > len(data):
        raise ValueError('Invalid decode range')
    output=bytearray(length)
    for index in range(0,length,2):
        position=offset+index
        code=(data[position]<<8)|data[position+1]
        code=DE[_address_bits(code,base+position)]^key
        output[index]=code>>8;output[index+1]=code&255
    return bytes(output)
