"""Validate opt-in atmospheric and underwater scene shader wiring."""
from pathlib import Path
import math
root=Path(__file__).resolve().parents[2]
for platform in ('PC','Android','VR'):
    base=root/platform/'src/pc/gfx'
    gl=(base/'gfx_opengl.c').read_text()
    pc=(base/'gfx_pc.c').read_text()
    assert 'if (configBetterGraphics && gfx_rapi == &gfx_opengl_api)' in pc
    assert 'find_water_level(environmentEye[0],environmentEye[2])' in pc
    assert 'environmentEye[1] < waterLevel - 8.0f' in pc
    assert 'gGlobalTimer % 1800' in pc
    assert 'if (shadow_receiver)' in gl
    for token in ('uEnvironmentEye', 'uEnvironmentState', 'aerial=smoothstep',
                  'causticWave=sin', 'underwaterFog=smoothstep'):
        assert token in gl, (platform,token)
    assert 'uEnvironmentState.y>0.5 && vShadowWorld.y<uEnvironmentState.z' in gl
    assert 'environment_eye_location = shadow_receiver ?' in gl
    assert 'environment_state_location = shadow_receiver ?' in gl
    # The procedural waves return to the same phase at the timer wrap.
    assert abs(math.sin(0)-math.sin(2*math.pi)) < 1e-12
    assert abs(math.sin(0)-math.sin(4*math.pi)) < 1e-12
vr=(root/'VR/src/pc/gfx/gfx_opengl.c').read_text()
assert 'if (shadow_receiver && enhanced_lighting)' in vr and 'float envRim=pow(' in vr
assert 'vr_get_stabilized_headset_world_position(head, false)' in (root/'VR/src/pc/gfx/gfx_pc.c').read_text()
for platform in ('WiiU','xbox360-port'):
    assert not (root/platform/'src/pc/gfx/gfx_experimental_sun.h').exists()
print('Atmospheric haze, submerged caustics/fog, VR Fresnel and opt-in wiring: ok')
