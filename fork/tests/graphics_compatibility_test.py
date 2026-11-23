"""Keep the selectable low-cost path and default-safe Android wiring intact."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for platform in ('PC','Android','VR'):
    base=root/platform/'src/pc'
    config=(base/'configfile.c').read_text()
    header=(base/'configfile.h').read_text()
    ui=(base/'djui/djui_panel_display.c').read_text()
    gfx=(base/'gfx/gfx_pc.c').read_text()
    default='false'
    assert f'configBetterGraphicsCompatibility    = {default};' in config
    assert '"better_graphics_compatibility"' in config and '&configBetterGraphicsCompatibility' in config
    assert 'extern bool configBetterGraphicsCompatibility;' in header
    assert '"Better Graphics Compatibility Mode", &configBetterGraphicsCompatibility' in ui
    assert 'if (configBetterGraphics && configBetterGraphicsShadows && !configBetterGraphicsCompatibility) {' in gfx
    assert 'sShadowVertices && configBetterGraphics && configBetterGraphicsShadows && !configBetterGraphicsCompatibility' in gfx
    assert 'want_shadow = configBetterGraphics && configBetterGraphicsShadows && !configBetterGraphicsCompatibility' in gfx
    assert '!dropped_frame && configBetterGraphics && configBetterGraphicsPost && !configBetterGraphicsCompatibility' in gfx
    assert 'configBetterGraphics && configBetterGraphicsSheen && sPlayerSheen && !gFullbright' in gfx
    # Compatibility does not erase the user's graphics setting or block its light path.
    assert 'configBetterGraphics = false' not in gfx
    if platform != 'VR':
        assert 'if (configBetterGraphics && !gFullbright)' in gfx
        assert 'return configBetterGraphics && configBetterGraphicsShadows && !configBetterGraphicsCompatibility' in gfx
    else:
        geo=(root/platform/'src/game/rendering_graph_node.c').read_text()
        assert '(configBetterGraphics && configBetterGraphicsShadows && !configBetterGraphicsCompatibility) ||' in geo
        assert 'want_enhanced_lighting = configBetterGraphics && !gFullbright' in gfx
for platform in ('WiiU','xbox360-port'):
    for file in ('src/pc/configfile.h','src/pc/configfile.c'):
        path=root/platform/file
        if path.exists(): assert 'configBetterGraphicsCompatibility' not in path.read_text()
print('Compatibility setting, defaults, legacy shadow fallback and platform exclusions: ok')
