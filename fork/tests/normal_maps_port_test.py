"""Validate the shipped normal-map bundles, opt-in wiring and platform packaging."""
from pathlib import Path
import hashlib, struct
root=Path(__file__).resolve().parents[2]
original=(root/'VR/assets/normal_maps.bin').read_bytes()
magic, version, count, offset=struct.unpack_from('<IIII',original)
assert (magic,version,count,offset)==(0x50414D4E,1,871,16)
for tree in ('PC','Android'):
    base=root/tree
    data=(base/'assets/normal_maps.bin').read_bytes()
    assert hashlib.sha256(data).digest()==hashlib.sha256(original).digest()
    for i in range(count):
        pos,size,w,h=struct.unpack_from('<IIII', data, offset+16*i)
        assert w and h and size==w*h*3 and pos+size <= len(data)
    gfx=(base/'src/pc/gfx/gfx_pc.c').read_text()
    gl=(base/'src/pc/gfx/gfx_opengl.c').read_text()
    assert 'gfx_normal_maps_clear_pending_texture_name();' in gfx
    assert 'dynos_texture_get_from_data' in gfx
    assert 'configBetterGraphics && configBetterGraphicsNormalMaps' in gfx
    assert 'gfx_normal_maps_load_pending(&normal' in gl
    assert 'GL_TEXTURE3 + opengl_curtex' in gl # unit 2 is the shadow map
    assert 'GL_LINEAR_MIPMAP_LINEAR' in gl and 'normal_clamp_edges' in gl
    assert 'append_normal_map_shader(fs_buf' in gl
    assert 'gfx_normal_maps_on_rom_loaded();' in (base/'src/pc/pc_main.c').read_text()
    print(tree, 'normal map bundle and opt-in renderer wiring: ok')
assert 'assets/normal_maps.bin' in (root/'Android/platform/app/build.gradle').read_text()
assert 'cp assets/normal_maps.bin $(APP_RESOURCES_DIR)' in (root/'PC/Makefile').read_text()
assert 'cp ../../assets/normal_maps.bin ../../../out/Realism64/' in (root/'.github/workflows/build-fork.yml').read_text()
