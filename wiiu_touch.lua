local REQUEST = "gore_wiiu_touch_request"
local FLING = "gore_wiiu_touch_fling"
local lastRequest = {}

local function player_at(i)
    if type(i) ~= "number" or i < 0 or i >= MAX_PLAYERS or i % 1 ~= 0 then return nil end
    local np = gNetworkPlayers[i]
    if np == nil or not np.connected then return nil end
    return np
end

local function same_area(a, b)
    return a ~= nil and b ~= nil and a.currAreaSyncValid and b.currAreaSyncValid
        and a.currCourseNum == b.currCourseNum and a.currActNum == b.currActNum
        and a.currLevelNum == b.currLevelNum and a.currAreaIndex == b.currAreaIndex
end

local function local_index(global)
    if type(global) ~= "number" or global % 1 ~= 0 or global < 0 or global >= MAX_PLAYERS then return nil end
    local i = network_local_index_from_global(global)
    if player_at(i) == nil then return nil end
    return i
end

local function fling_local(attackerIndex, clientChoice)
    if clientChoice and (gOpt == nil or not gOpt.wiiu_receive_fling) then return end
    if attackerIndex == nil or attackerIndex <= 0 then return end
    local attacker, victim = gMarioStates[attackerIndex], gMarioStates[0]
    if attacker == nil or victim == nil or attacker.marioObj == nil or victim.marioObj == nil then return end
    if not same_area(player_at(attackerIndex), player_at(0)) then return end
    if not gore_true(is_player_active(attacker)) or not gore_true(is_player_active(victim)) then return end
    gore_fling(victim, attacker.marioObj, 60, true)
end

local function host_fling(attackerIndex, victimIndex)
    local attacker, victim = player_at(attackerIndex), player_at(victimIndex)
    if attacker == nil or victim == nil or attackerIndex == victimIndex or not same_area(attacker, victim) then return end
    if gOpt == nil then return end
    local clientChoice = not gOpt.wiiu_host_control
    if victimIndex == 0 then
        fling_local(attackerIndex, clientChoice)
    else
        network_send_to(victimIndex, true, { type = FLING, attacker = attacker.globalIndex, clientChoice = clientChoice })
    end
end

local function packet_receive(data)
    if type(data) ~= "table" or gore_packet_sender == nil then return end
    local sender = gore_packet_sender()
    if player_at(sender) == nil or sender <= 0 then return end
    if network_is_server() and data.type == REQUEST then
        if gOpt == nil or (gOpt.wiiu_host_control and not gOpt.wiiu_touch_fling) then return end
        local victim = local_index(data.victim)
        if victim == nil then return end
        local now = get_global_timer()
        local last = lastRequest[sender]
        if last ~= nil and now >= last and now - last < 5 then return end
        lastRequest[sender] = now
        host_fling(sender, victim)
    elseif not network_is_server() and data.type == FLING then
        local host = local_index(0)
        if host == nil or sender ~= host then return end
        if type(data.clientChoice) ~= "boolean" then return end
        local attacker = local_index(data.attacker)
        fling_local(attacker, data.clientChoice)
    end
end

hook_event(HOOK_ON_PACKET_RECEIVE, packet_receive)

if wiiu_touch_pressed ~= nil then
    local function is_visible(m, np)
        if m == nil or m.marioObj == nil or np == nil or not np.connected or not np.currAreaSyncValid then return false end
        if not same_area(player_at(0), np) or not gore_true(is_player_active(m)) then return false end
        local flags = m.marioObj.header.gfx.node.flags
        if (flags & GRAPH_RENDER_ACTIVE) == 0 or (flags & GRAPH_RENDER_INVISIBLE) ~= 0 then return false end
        if np.fadeOpacity ~= nil and np.fadeOpacity == 0 then return false end
        return true
    end

    local function unobstructed(pos)
        if gLakituState == nil or gLakituState.pos == nil or collision_find_surface_on_ray == nil then return false end
        local camera = gLakituState.pos
        local dx, dy, dz = pos.x - camera.x, pos.y - camera.y, pos.z - camera.z
        local hit = collision_find_surface_on_ray(camera.x, camera.y, camera.z, dx, dy, dz)
        if hit == nil or hit.hitPos == nil then return false end
        local hx, hy, hz = hit.hitPos.x - pos.x, hit.hitPos.y - pos.y, hit.hitPos.z - pos.z
        return hx * hx + hy * hy + hz * hz < 2500
    end

    local function tapped_player(x, y)
        local width, height = djui_hud_get_screen_width(), djui_hud_get_screen_height()
        x, y = x * width, y * height
        local best, bestDepth
        for i = 1, MAX_PLAYERS - 1 do
            local m, np = gMarioStates[i], player_at(i)
            if is_visible(m, np) then
                local pos = m.marioObj.header.gfx.pos
                local scale = m.marioObj.header.gfx.scale.y
                if scale <= 0 then scale = 1 end
                local foot, head = { x = pos.x, y = pos.y, z = pos.z }, { x = pos.x, y = pos.y + 200 * scale, z = pos.z }
                local a, b = { x = 0, y = 0, z = 0 }, { x = 0, y = 0, z = 0 }
                if djui_hud_world_pos_to_screen_pos(foot, a) and djui_hud_world_pos_to_screen_pos(head, b) then
                    local top, bottom = math.min(a.y, b.y), math.max(a.y, b.y)
                    local halfWidth = (bottom - top) * 0.32
                    local centerX = (a.x + b.x) * 0.5
                    if bottom >= 0 and top <= height and centerX + halfWidth >= 0 and centerX - halfWidth <= width
                        and x >= centerX - halfWidth and x <= centerX + halfWidth and y >= top and y <= bottom
                        and (bestDepth == nil or a.z > bestDepth) then
                        local middle = { x = pos.x, y = pos.y + 100 * scale, z = pos.z }
                        if unobstructed(middle) then best, bestDepth = i, a.z end
                    end
                end
            end
        end
        return best
    end

    local function on_hud_render()
        local x, y = wiiu_touch_pressed()
        if x == nil or y == nil then return end
        if x < 0 or x > 1 or y < 0 or y > 1 then return end
        if djui_hud_is_pause_menu_created() or (djui_console_is_open ~= nil and djui_console_is_open()) then return end
        if not network_is_server() and (gOpt == nil or (gOpt.wiiu_host_control and not gOpt.wiiu_touch_fling)) then return end
        local resolution = djui_hud_get_resolution()
        djui_hud_set_resolution(RESOLUTION_N64)
        local victim = tapped_player(x, y)
        djui_hud_set_resolution(resolution)
        if victim == nil then return end
        if network_is_server() then
            host_fling(0, victim)
        else
            local host = local_index(0)
            if host ~= nil then network_send_to(host, true, { type = REQUEST, victim = gNetworkPlayers[victim].globalIndex }) end
        end
    end
    hook_event(HOOK_ON_HUD_RENDER, on_hud_render)
end
