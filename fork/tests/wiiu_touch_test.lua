local script = arg[1] or "wiiu_touch.lua"
local function environment(server, localGlobal, permission)
    local env = setmetatable({}, {__index = _G})
    env.MAX_PLAYERS = 4
    env.HOOK_ON_PACKET_RECEIVE, env.HOOK_ON_HUD_RENDER = 1, 2
    env.RESOLUTION_N64 = 1
    env.GRAPH_RENDER_ACTIVE, env.GRAPH_RENDER_INVISIBLE = 1, 16
    env.hooks, env.sent, env.flings = {}, {}, {}
    env.gOpt = { wiiu_touch_fling = permission }
    env.timer, env.sender, env.touch = 100, nil, nil
    env.gLakituState = { pos = { x = 0, y = 0, z = 0 } }
    env.gNetworkPlayers, env.gMarioStates = {}, {}
    local slots = {localGlobal}
    for i = 0, 2 do if i ~= localGlobal then slots[#slots + 1] = i end end
    for i, g in ipairs(slots) do
        local n = i - 1
        env.gNetworkPlayers[n] = { connected = true, globalIndex = g, currAreaSyncValid = true,
            currCourseNum = 1, currActNum = 1, currLevelNum = 1, currAreaIndex = 1, fadeOpacity = 255 }
        local pos = { x = (g == 2 and 0 or 2), y = 0, z = g == 2 and -400 or -700 }
        env.gMarioStates[n] = { marioObj = { header = { gfx = { pos = pos, scale = { y = 1 }, node = { flags = 1 } } } }, id = g }
    end
    env.network_is_server = function() return server end
    env.network_local_index_from_global = function(g)
        for i = 0, 2 do if env.gNetworkPlayers[i].globalIndex == g then return i end end
    end
    env.hook_event = function(h, f) env.hooks[h] = f end
    env.gore_packet_sender = function() return env.sender end
    env.get_global_timer = function() return env.timer end
    env.network_send_to = function(i, reliable, data) env.sent[#env.sent+1] = { i = i, reliable = reliable, data = data } end
    env.gore_true = function(v) return v ~= false and v ~= 0 and v ~= nil end
    env.is_player_active = function() return 1 end
    env.gore_fling = function(victim, source, power, still) env.flings[#env.flings+1] = { victim = victim, source = source, power = power, still = still } end
    env.wiiu_touch_pressed = function() if not env.touch then return end local t=env.touch; env.touch=nil; return t[1],t[2] end
    env.djui_hud_is_pause_menu_created = function() return env.paused end
    env.djui_console_is_open = function() return env.console end
    env.djui_hud_get_resolution = function() return env.resolution or 7 end
    env.djui_hud_set_resolution = function(v) env.resolution = v end
    env.djui_hud_get_screen_width = function() return 320 end
    env.djui_hud_get_screen_height = function() return 240 end
    env.djui_hud_world_pos_to_screen_pos = function(pos, out)
        out.x = 160 + pos.x
        out.y = 200 - pos.y / 2
        out.z = pos.z
        return pos.z < 0
    end
    env.collision_find_surface_on_ray = function(x, y, z, dx, dy, dz)
        if env.blocked then return {hitPos = {x=x,y=y,z=z}} end
        return {hitPos = {x=x+dx,y=y+dy,z=z+dz}}
    end
    assert(loadfile(script, 't', env))()
    return env
end
local host = environment(true, 0, false)
host.touch = {0.5, 0.6}; host.hooks[2]()
assert(#host.sent == 1 and host.sent[1].i == 2 and host.sent[1].data.attacker == 0, 'host tap selects nearest')
assert(host.resolution == 7, 'restores hud resolution')
host.sent = {}; host.paused = true; host.touch = {0.5, 0.6}; host.hooks[2](); assert(#host.sent==0, 'pause blocks')
host.paused = false; host.blocked = true; host.touch = {0.5,0.6}; host.hooks[2](); assert(#host.sent==0, 'wall blocks')
host.blocked = false; host.gMarioStates[2].marioObj.header.gfx.node.flags = 16; host.touch={0.5,0.6}; host.hooks[2](); assert(#host.sent==1 and host.sent[1].i==1, 'hidden player skipped')
host.sent = {}; host.gMarioStates[2].marioObj.header.gfx.node.flags=1; host.sender = 1
host.hooks[1]({type='gore_wiiu_touch_request', victim=2}); assert(#host.sent==0, 'disabled permission blocks client')
host.gOpt.wiiu_touch_fling = true
host.hooks[1]({type='gore_wiiu_touch_request', victim=2}); assert(#host.sent==1 and host.sent[1].data.attacker==1, 'enabled request forwarded')
host.hooks[1]({type='gore_wiiu_touch_request', victim=2}); assert(#host.sent==1, 'rate limit')
host.timer = 110; host.hooks[1]({type='gore_wiiu_touch_request', victim=0}); assert(#host.flings==1 and host.flings[1].victim.id==0, 'host victim owner flings')
host.timer = 120; host.gNetworkPlayers[2].currAreaIndex=2; host.hooks[1]({type='gore_wiiu_touch_request', victim=2}); assert(#host.sent==1, 'different areas blocked')
local client = environment(false, 2, false)
client.touch = {0.5,0.6}; client.hooks[2](); assert(#client.sent==0, 'disabled client touch')
client.gOpt.wiiu_touch_fling = true
client.touch = {0.5,0.6}; client.hooks[2](); assert(#client.sent==1 and client.sent[1].data.type=='gore_wiiu_touch_request', 'client sends host request')
client.sender = client.network_local_index_from_global(1)
client.hooks[1]({type='gore_wiiu_touch_fling', attacker=1}); assert(#client.flings==0, 'forged non-host ignored')
client.gOpt.wiiu_touch_fling = false
client.sender = client.network_local_index_from_global(0)
client.hooks[1]({type='gore_wiiu_touch_fling', attacker=1}); assert(#client.flings==1 and client.flings[1].victim.id==2 and client.flings[1].power==60, 'host fling runs on owning client')
client.hooks[1]({type='gore_wiiu_touch_fling', attacker=9}); assert(#client.flings==1, 'invalid attacker ignored')
print('lua tap tests passed')
