-- Local instruments. Register only the hooks that this client can use;
-- none of these features change Mario state or send multiplayer packets.
local platform = get_os_name()
local enabled = true
local function toggle(label)
    hook_chat_command("fieldkit", "- Toggle " .. label, function()
        enabled = not enabled
        djui_chat_message_create(label .. (enabled and ": on" or ": off"))
        return true
    end)
end

if vr_net_state ~= nil then
    -- Bring tracked palms together to check vitality without a fixed HUD.
    toggle("VR pulse check")
    hook_chat_command("reach", "- Measure the span between tracked hands", function()
        local h = vr_net_state()
        if not h or h[3] == 0 or h[8] == 0 then
            djui_chat_message_create("Track both hands to measure reach.")
        else
            local dx, dy, dz = h[5]-h[10], h[6]-h[11], h[7]-h[12]
            djui_chat_message_create(string.format("Hand span: %.0f game units", math.sqrt(dx*dx + dy*dy + dz*dz)))
        end
        return true
    end)
    local held, armed = 0, true
    hook_event(HOOK_UPDATE, function()
        if not enabled then held, armed = 0, true; return end
        local hand = vr_net_state()
        if not hand or hand[3] == 0 or hand[8] == 0 then held = 0; return end
        local x, y, z = hand[5]-hand[10], hand[6]-hand[11], hand[7]-hand[12]
        local d2 = x*x + y*y + z*z
        if d2 > 60*60 then armed = true end
        if not armed or d2 > 35*35 then held = 0; return end
        held = held + 1
        if held == 15 then
            armed = false
            djui_popup_create(string.format("Pulse check: %d / 8 health", math.min(8, gMarioStates[0].health >> 8)), 1)
        end
    end)
elseif platform == "Xbox 360" then
    toggle("Controller heartbeat and landing feedback")
    local ticks, fallSpeed = 0, 0
    hook_event(HOOK_ON_WARP, function() fallSpeed = 0 end)
    hook_event(HOOK_MARIO_UPDATE, function(m)
        if m.playerIndex ~= 0 then return end
        local pad = m.controller
        if (pad.buttonDown & L_TRIG) ~= 0 and (pad.buttonPressed & U_JPAD) ~= 0 then
            djui_popup_create(string.format("Status: %d/8 health | %d coins | %d stars",
                math.min(8, m.health >> 8), m.numCoins, m.numStars), 1)
        end
        if enabled and (m.action & ACT_FLAG_AIR) ~= 0 then
            fallSpeed = math.max(0, -m.vel.y)
        else
            if enabled and fallSpeed >= 40 and math.abs(m.pos.y - m.floorHeight) < 5 then
                queue_rumble_data(5, math.min(100, math.floor(fallSpeed)))
                ticks = 1 -- don't overwrite the landing pulse with a heartbeat this frame
            end
            fallSpeed = 0
        end
        if not enabled or m.health < 0x100 or m.health >= 0x400 then ticks = 0; return end
        if ticks == 0 then queue_rumble_data(3, 45) end
        ticks = (ticks + 1) % (m.health < 0x200 and 16 or 30)
    end)
elseif platform == "Android" then
    toggle("Dive warning and coin milestones")
    local warned, lastCoins = false, nil
    hook_event(HOOK_ON_WARP, function() lastCoins = nil end)
    hook_event(HOOK_MARIO_UPDATE, function(m)
        if m.playerIndex ~= 0 then return end
        if enabled and lastCoins and m.numCoins // 25 > lastCoins // 25 then
            djui_popup_create(string.format("Coin milestone: %d", (m.numCoins // 25) * 25), 1)
        end
        lastCoins = m.numCoins
        if not enabled or (m.action & ACT_FLAG_SWIMMING) == 0 or m.health >= 0x500 then
            warned = false
        elseif not warned and m.health >= 0x100 and m.health < 0x400 and m.pos.y < m.waterLevel - 80 then
            warned = true
            djui_popup_create("Low air - swim up!", 1)
        end
    end)
elseif platform == "Wii U" then
    local mark
    hook_event(HOOK_ON_WARP, function() mark = nil end)
    hook_chat_command("trail", "[mark|clear] - Remember a spot and check the way back", function(arg)
        local p = gMarioStates[0].pos
        if arg == "mark" then
            mark = {x=p.x, y=p.y, z=p.z}
            djui_chat_message_create("Trail marker set.")
        elseif arg == "clear" then
            mark = nil
            djui_chat_message_create("Trail marker cleared.")
        elseif mark then
            djui_chat_message_create(string.format("Back to marker: X %+.0f, Y %+.0f, Z %+.0f", mark.x-p.x, mark.y-p.y, mark.z-p.z))
        else
            djui_chat_message_create("Use /trail mark to remember this spot.")
        end
        return true
    end)
    -- A local co-op spotter; unlike the GamePad's tap-to-fling this never
    -- targets or moves another player (and doesn't consume the touch event).
    hook_chat_command("spotter", "- Find the closest teammate in this area", function()
        local me, nearest, best = gNetworkPlayers[0], nil, math.huge
        for i = 1, MAX_PLAYERS - 1 do
            local np = gNetworkPlayers[i]
            if np.connected and np.currAreaSyncValid and me.currAreaSyncValid and np.currCourseNum == me.currCourseNum
                and np.currActNum == me.currActNum and np.currLevelNum == me.currLevelNum and np.currAreaIndex == me.currAreaIndex then
                local p, q = gMarioStates[0].pos, gMarioStates[i].pos
                local d = (p.x-q.x)^2 + (p.y-q.y)^2 + (p.z-q.z)^2
                if d < best then nearest, best = np.name, d end
            end
        end
        djui_chat_message_create(nearest and string.format("Nearest: %s (%d units)", nearest, math.floor(math.sqrt(best))) or "No teammates in this area.")
        return true
    end)
elseif platform == "Windows" or platform == "Linux" or platform == "Mac OSX" or platform == "FreeBSD" or platform == "Unix" then
    local tracking, launch, apex = false, nil, nil
    hook_chat_command("jumpstats", "- Toggle jump measurements", function()
        tracking, launch = not tracking, nil
        djui_chat_message_create(tracking and "Jump stats on." or "Jump stats off.")
        return true
    end)
    hook_event(HOOK_ON_WARP, function() launch = nil end)
    hook_event(HOOK_MARIO_UPDATE, function(m)
        if not tracking or m.playerIndex ~= 0 then return end
        local p = m.pos
        if (m.action & ACT_FLAG_AIR) ~= 0 then
            if not launch and m.vel.y > 0 then
                launch, apex = {x=p.x, y=p.y, z=p.z}, p.y
            end
            if launch then apex = math.max(apex, p.y) end
        elseif launch then
            if math.abs(p.y-m.floorHeight) < 5 then
                local dx, dz = p.x-launch.x, p.z-launch.z
                djui_chat_message_create(string.format("Jump: %.0f units across, %.0f up", math.sqrt(dx*dx+dz*dz), apex-launch.y))
            end
            launch = nil
        end
    end)
    local start, previous
    hook_chat_command("split", "[start|stop] - Record a practice split", function(arg)
        local now = get_global_timer()
        if arg == "start" then
            start, previous = now, now
            djui_chat_message_create("Practice timer started.")
        elseif start and (arg == "" or arg == "stop") then
            djui_chat_message_create(string.format("Total %.2fs | Split %.2fs", (now-start)/30, (now-previous)/30))
            previous = now
            if arg == "stop" then start = nil end
        else
            djui_chat_message_create("Use /split start, /split, then /split stop.")
        end
        return true
    end)
end
