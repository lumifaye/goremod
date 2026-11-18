
local MAGIC      = 0xB7
local PKT_POSE   = 1
local PKT_HIT    = 2
local PKT_EVENT  = 3

local SEND_EVERY = 2
local STALE      = 20
local MAX_FX     = 45

local FLAG_FIRE_FLOWER = 1
local FLAG_HAMMER_SUIT = 2
local FLAG_SONIC_SHOES = 4
local FLAG_BIG_HANDS   = 8
local FLAG_PROPELLER   = 16
local FLAG_POWER_STAR  = 32

local HAND_L_VALID, HAND_L_CLOSED, HAND_R_VALID, HAND_R_CLOSED = 1, 2, 4, 8
local HAND_L_HAT, HAND_R_HAT = 16, 32
local HAT_SHIFT = 6
local HAT_NORMAL, HAT_WING, HAT_METAL, HAT_VANISH = 0, 1, 2, 3

local EVENT_LEVEL_SELECT = 1

local FX_FIREBALL, FX_FIREBALL_CHARGE, FX_HAMMER, FX_HAMMER_CHARGE, FX_RASENGAN, FX_SHURIKEN = 1, 2, 3, 4, 5, 6
local FX_ITEM_FIRE_FLOWER, FX_ITEM_HAMMER_SUIT, FX_ITEM_SONIC_SHOES = 7, 8, 9
local FX_ITEM_BIG_HANDS, FX_ITEM_PROPELLER, FX_ITEM_POWER_STAR = 10, 11, 12
local FX_CAP_WING, FX_CAP_VANISH, FX_CAP_METAL, FX_CAP_NORMAL = 13, 14, 15, 16

local sFxLook = {
    [FX_FIREBALL]         = { model = E_MODEL_RED_FLAME,        scale = 3.0, anim = true },
    [FX_FIREBALL_CHARGE]  = { model = E_MODEL_RED_FLAME,        scale = 1.8, anim = true },
    [FX_HAMMER]           = { model = E_MODEL_METALLIC_BALL,    scale = 0.4 },
    [FX_HAMMER_CHARGE]    = { model = E_MODEL_METALLIC_BALL,    scale = 0.4 },
    [FX_RASENGAN]         = { model = E_MODEL_BLUE_FLAME,       scale = 3.5, anim = true },
    [FX_SHURIKEN]         = { model = E_MODEL_BLUE_FLAME,       scale = 6.0, anim = true },
    [FX_ITEM_FIRE_FLOWER] = { model = E_MODEL_RED_FLAME_SHADOW, scale = 2.0, anim = true },
    [FX_ITEM_HAMMER_SUIT] = { model = E_MODEL_METALLIC_BALL,    scale = 0.7 },
    [FX_ITEM_SONIC_SHOES] = { model = E_MODEL_BLUE_COIN,        scale = 1.2, anim = true },
    [FX_ITEM_BIG_HANDS]   = { model = E_MODEL_WHITE_PARTICLE,   scale = 2.5 },
    [FX_ITEM_PROPELLER]   = { model = E_MODEL_1UP,              scale = 1.0 },
    [FX_ITEM_POWER_STAR]  = { model = E_MODEL_STAR,             scale = 1.0, solid = true, spin = true },
    [FX_CAP_WING]         = { model = E_MODEL_MARIOS_WING_CAP,  scale = 1.0, solid = true, spin = true },
    [FX_CAP_VANISH]       = { model = E_MODEL_MARIOS_CAP,       scale = 1.0, solid = true, spin = true },
    [FX_CAP_METAL]        = { model = E_MODEL_MARIOS_METAL_CAP, scale = 1.0, solid = true, spin = true },
    [FX_CAP_NORMAL]       = { model = E_MODEL_MARIOS_CAP,       scale = 1.0, solid = true },
}

local sHatLook = {
    [HAT_NORMAL] = { model = E_MODEL_MARIOS_CAP,       scale = 1.0, solid = true },
    [HAT_WING]   = { model = E_MODEL_MARIOS_WING_CAP,  scale = 1.0, solid = true },
    [HAT_METAL]  = { model = E_MODEL_MARIOS_METAL_CAP, scale = 1.0, solid = true },
    [HAT_VANISH] = { model = E_MODEL_MARIOS_CAP,       scale = 1.0, solid = true },
}

local sGloveLook = { model = E_MODEL_WHITE_PARTICLE, scale = 1.0 }
local GLOVE_OPEN   = 1.15
local GLOVE_CLOSED = 0.9

local sCanPack = string.pack ~= nil and string.unpack ~= nil
    and network_send_bytestring ~= nil and HOOK_ON_PACKET_BYTESTRING_RECEIVE ~= nil

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

local function s16(v)
    return clamp(math.floor(v + 0.5), -32768, 32767)
end

function gore_vr_angle(v)
    v = math.floor(v + 0.5) % 65536
    if v >= 32768 then v = v - 65536 end
    return v
end


local HEAD_EYES   = 1
local HEAD_ANGLES = 2
local HEAD_FIRST  = 4
local HEAD_TURNS  = 8
local HEAD_TURNED = 16

local function s8(v)
    return clamp(math.floor(v * 127 + 0.5), -127, 127)
end

function gore_vr_encode_pose(globalIndex, state)
    local n = math.min(#state.fx, MAX_FX)
    local parts = { string.pack("<BBBBBBhhhhhhB", MAGIC, PKT_POSE, globalIndex, state.flags & 0xFF, state.hands & 0xFF,
        clamp(math.floor(state.bigScale * 32 + 0.5), 0, 255),
        s16(state.lx), s16(state.ly), s16(state.lz), s16(state.rx), s16(state.ry), s16(state.rz), n) }
    for i = 1, n do
        local fx = state.fx[i]
        parts[#parts + 1] = string.pack("<Bhhh", fx[1] & 0xFF, s16(fx[2]), s16(fx[3]), s16(fx[4]))
    end
    if state.head ~= nil then
        local turns = state.turns
        parts[#parts + 1] = string.pack("<Bhhh",
            HEAD_EYES | HEAD_ANGLES | (state.first and HEAD_FIRST or 0) | (turns ~= nil and HEAD_TURNS or 0)
                | (state.turned and HEAD_TURNED or 0),
            gore_vr_angle(state.head[1]), gore_vr_angle(state.head[2]), gore_vr_angle(state.head[3]))
        if turns ~= nil then
            parts[#parts + 1] = string.pack("<bbbbbbbbbbbb",
                s8(turns[1]), s8(turns[2]), s8(turns[3]), s8(turns[4]), s8(turns[5]), s8(turns[6]),
                s8(turns[7]), s8(turns[8]), s8(turns[9]), s8(turns[10]), s8(turns[11]), s8(turns[12]))
        end
    end
    return table.concat(parts)
end

function gore_vr_decode_pose(bytes)
    if #bytes < 19 then return nil end
    local _, _, gi, flags, hands, big, lx, ly, lz, rx, ry, rz, n = string.unpack("<BBBBBBhhhhhhB", bytes)
    if n > MAX_FX or #bytes < 19 + n * 7 then return nil end
    local state = { flags = flags, hands = hands, bigScale = big / 32, lx = lx, ly = ly, lz = lz, rx = rx, ry = ry, rz = rz, fx = {} }
    local at = 20
    for i = 1, n do
        local kind, x, y, z
        kind, x, y, z, at = string.unpack("<Bhhh", bytes, at)
        state.fx[i] = { kind, x, y, z }
    end
    if #bytes >= at + 6 then
        local bits, yaw, pitch, roll
        bits, yaw, pitch, roll, at = string.unpack("<Bhhh", bytes, at)
        if bits & HEAD_EYES ~= 0 and bits & HEAD_ANGLES ~= 0 then
            state.head = { yaw, pitch, roll }
            state.first = bits & HEAD_FIRST ~= 0
            state.turned = bits & HEAD_TURNED ~= 0 and not state.first
            if bits & HEAD_TURNS ~= 0 and #bytes >= at + 11 then
                local turns = { string.unpack("<bbbbbbbbbbbb", bytes, at) }
                turns[13] = nil
                for i = 1, 12 do turns[i] = turns[i] / 127 end
                state.turns = turns
            end
        end
    end
    return gi, state
end

function gore_vr_encode_hit(attackerGlobal, victimGlobal, attackType, yaw)
    return string.pack("<BBBBBh", MAGIC, PKT_HIT, attackerGlobal, victimGlobal, attackType, s16(yaw))
end

function gore_vr_decode_hit(bytes)
    if #bytes < 7 then return nil end
    local _, _, attacker, victim, attackType, yaw = string.unpack("<BBBBBh", bytes)
    return attacker, victim, attackType, yaw
end

function gore_vr_encode_event(senderGlobal, kind, a)
    return string.pack("<BBBBh", MAGIC, PKT_EVENT, senderGlobal, kind & 0xFF, s16(a))
end

function gore_vr_decode_event(bytes)
    if #bytes < 6 then return nil end
    local _, _, sender, kind, a = string.unpack("<BBBBh", bytes)
    return sender, kind, a
end

local sRemote = {}
local sGloves = {}
local sHats   = {}
local sFx     = {}
local sLooks  = {}

function gore_vr_remote(globalIndex)
    local r = sRemote[globalIndex]
    return r and r.state
end

local PROP_ANIM, PROP_SPIN = 1, 2

local function prop_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
    o.header.gfx.skipInViewCheck = true
end

local function prop_loop(o)
    if o.oTimer > o.oHealth + STALE then
        obj_mark_for_deletion(o)
        return
    end
    local how = o.oBehParams2ndByte
    if how & PROP_ANIM ~= 0 then o.oAnimState = o.oAnimState + 1 end
    if how & PROP_SPIN ~= 0 then o.oFaceAngleYaw = o.oFaceAngleYaw + 0x800 end
end

id_bhvGoreVrProp = hook_behavior(nil, OBJ_LIST_UNIMPORTANT, true, prop_init, prop_loop, "bhvGoreVrProp")

local function prop_alive(o)
    return o ~= nil and o.activeFlags ~= ACTIVE_FLAG_DEACTIVATED and gore_true(obj_has_behavior_id(o, id_bhvGoreVrProp))
end

local function prop_place(o, look, x, y, z, scale, yaw)
    local model = look.model
    if not prop_alive(o) then
        o = spawn_non_sync_object(id_bhvGoreVrProp, model, x, y, z, function(obj)
            obj.oOpacity = 255
            obj.oBehParams = model
        end)
        if o == nil then return nil end
    else
        local dx, dy, dz = x - o.oPosX, y - o.oPosY, z - o.oPosZ
        if dx * dx + dy * dy + dz * dz < 600 * 600 then
            x, y, z = o.oPosX + dx * 0.6, o.oPosY + dy * 0.6, o.oPosZ + dz * 0.6
        end
        o.oPosX, o.oPosY, o.oPosZ = x, y, z
    end
    if o.oBehParams ~= model then
        obj_set_model_extended(o, model)
        o.oBehParams = model
    end
    local node = o.header.gfx.node
    if look.solid then
        node.flags = node.flags & ~GRAPH_RENDER_BILLBOARD
    else
        node.flags = node.flags | GRAPH_RENDER_BILLBOARD
    end
    obj_scale(o, scale or look.scale)
    o.oBehParams2ndByte = (look.anim and PROP_ANIM or 0) | (look.spin and PROP_SPIN or 0)
    if yaw ~= nil and not look.spin then o.oFaceAngleYaw = yaw end
    o.oHealth = o.oTimer
    return o
end

local function prop_remove(o)
    if prop_alive(o) then obj_mark_for_deletion(o) end
end

local function set_part(np, part, r, g, b)
    if part == nil or network_player_set_override_palette_color == nil then return end
    network_player_set_override_palette_color(np, part, { r = r, g = g, b = b })
end

local function look_apply(globalIndex, np, flags)
    local wanted = flags & (FLAG_FIRE_FLOWER | FLAG_HAMMER_SUIT | FLAG_SONIC_SHOES)
    if sLooks[globalIndex] == wanted then return end
    if network_player_reset_override_palette ~= nil and (sLooks[globalIndex] or 0) ~= 0 then
        network_player_reset_override_palette(np)
    end
    sLooks[globalIndex] = wanted
    if wanted == 0 then return end
    if wanted & FLAG_FIRE_FLOWER ~= 0 then
        set_part(np, CAP, 255, 255, 255)
        set_part(np, SHIRT, 255, 255, 255)
        set_part(np, PANTS, 220, 20, 10)
    elseif wanted & FLAG_HAMMER_SUIT ~= 0 then
        set_part(np, CAP, 30, 30, 30)
        set_part(np, SHIRT, 30, 30, 30)
    end
    if wanted & FLAG_SONIC_SHOES ~= 0 then
        set_part(np, SHOES, 230, 20, 20)
    end
end

local function look_forget(globalIndex, np)
    if (sLooks[globalIndex] or 0) ~= 0 and np ~= nil and network_player_reset_override_palette ~= nil then
        network_player_reset_override_palette(np)
    end
    sLooks[globalIndex] = nil
end

local function forget_props(globalIndex)
    prop_remove(sGloves[globalIndex * 2]);     sGloves[globalIndex * 2] = nil
    prop_remove(sGloves[globalIndex * 2 + 1]); sGloves[globalIndex * 2 + 1] = nil
    prop_remove(sHats[globalIndex]);           sHats[globalIndex] = nil
    local list = sFx[globalIndex]
    if list ~= nil then
        for i = 1, #list do prop_remove(list[i]) end
        sFx[globalIndex] = nil
    end
end

local function forget(globalIndex, np)
    forget_props(globalIndex)
    look_forget(globalIndex, np)
end

local EYES_UP    = 30
local NECK_UP    = 88
local GLIDE      = 0.6
local SNAP       = 4
local POSE_TURNS = 32 | 64
local BODY_EASE  = 0.5

local function glide_angle(from, to)
    return gore_vr_angle(from + gore_vr_angle(to - from) * GLIDE)
end

local function neck_of(m)
    local body = m.marioBodyState
    if body ~= nil and body.headPos ~= nil and body.updateHeadPosTime ~= nil
        and get_global_timer() - body.updateHeadPosTime <= 2 then
        return body.headPos.x, body.headPos.y, body.headPos.z
    end
    local size = (m.marioObj ~= nil) and m.marioObj.header.gfx.scale.y or 1
    return m.pos.x, m.pos.y + NECK_UP * size, m.pos.z
end

function gore_vr_body(r, m, neckX, neckY, neckZ)
    local state = r.state
    local want = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }
    local size = (m.marioObj ~= nil) and m.marioObj.header.gfx.scale.y or 1
    local nudge = (gOpt ~= nil and type(gOpt.vr_hand_height) == "number") and (gOpt.vr_hand_height - 40) or 0
    for hand = 0, 1 do
        if state.hands & (hand == 0 and HAND_L_VALID or HAND_R_VALID) ~= 0 then
            local x = hand == 0 and state.lx or state.rx
            local y = hand == 0 and state.ly or state.ry
            local z = hand == 0 and state.lz or state.rz
            if state.head ~= nil then
                y = y + EYES_UP * size
            else
                x, y, z = m.pos.x + x - neckX, m.pos.y + y - neckY, m.pos.z + z - neckZ
            end
            want[hand * 3 + 1], want[hand * 3 + 2], want[hand * 3 + 3] = x, y + nudge, z
        end
    end
    if state.head ~= nil then
        want[7], want[8], want[9] = state.head[1], state.head[2], state.head[3]
    end
    if state.turns ~= nil then
        for i = 1, 12 do want[9 + i] = state.turns[i] end
    end

    local shown = r.shown
    if shown == nil then
        r.shown, r.shownHands, r.shownHead, r.shownTurns = want, state.hands, state.head ~= nil, state.turns ~= nil
        r.shownTurned = state.turned == true
        return want
    end
    local glide = (r.snap or 0) > 0 and 1 or GLIDE
    for hand = 0, 1 do
        local bit = hand == 0 and HAND_L_VALID or HAND_R_VALID
        for i = hand * 3 + 1, hand * 3 + 3 do
            if r.shownHands & bit ~= 0 and state.hands & bit ~= 0 then
                shown[i] = shown[i] + (want[i] - shown[i]) * glide
            else
                shown[i] = want[i]
            end
        end
    end
    for i = 7, 9 do
        if r.shownHead and state.head ~= nil and r.shownTurned == (state.turned == true) then
            shown[i] = glide_angle(shown[i], want[i])
        else
            shown[i] = want[i]
        end
    end
    for hand = 0, 1 do
        local bit = hand == 0 and HAND_L_VALID or HAND_R_VALID
        local glides = r.shownTurns and state.turns ~= nil and r.shownHands & bit ~= 0 and state.hands & bit ~= 0
        for i = 10 + hand * 6, 15 + hand * 6 do
            shown[i] = glides and (shown[i] + (want[i] - shown[i]) * glide) or want[i]
        end
    end
    r.shownHands, r.shownHead, r.shownTurns = state.hands, state.head ~= nil, state.turns ~= nil
    r.shownTurned = state.turned == true
    return shown
end

local function body_follows(m)
    if m.health <= 0xff then return false end
    local group = m.action & ACT_GROUP_MASK
    if group ~= ACT_GROUP_STATIONARY and group ~= ACT_GROUP_MOVING and group ~= ACT_GROUP_AIRBORNE then return false end
    return m.action & (ACT_FLAG_INTANGIBLE | ACT_FLAG_INVULNERABLE | ACT_FLAG_DIVING
        | ACT_FLAG_BUTT_OR_STOMACH_SLIDE | ACT_FLAG_RIDING_SHELL) == 0
end

function gore_vr_body_yaw(body, head)
    local off = gore_vr_angle(head - body)
    if off > -0x100 and off < 0x100 then return gore_vr_angle(head) end
    return gore_vr_angle(body + off * BODY_EASE)
end

local function face_body(m, r)
    if r.shown == nil or not r.shownHead or r.state.first ~= true or m.marioObj == nil or not body_follows(m) then
        r.bodyYaw = nil
        return
    end
    local angle = m.marioObj.header.gfx.angle
    r.bodyYaw = gore_vr_body_yaw(r.bodyYaw or angle.y, r.shown[7])
    angle.y = r.bodyYaw
end

local function draw_player(globalIndex, r)
    local state = r.state
    local localIndex = network_local_index_from_global(globalIndex)
    if localIndex == nil or localIndex <= 0 or localIndex >= MAX_PLAYERS then return false end
    local np = gNetworkPlayers[localIndex]
    local m = gMarioStates[localIndex]
    if np == nil or m == nil or not np.connected then return false end

    look_apply(globalIndex, np, state.flags)

    if not gore_true(is_player_active(m)) then
        forget_props(globalIndex)
        r.shown = nil
        if vr_remote_pose ~= nil then vr_remote_pose(localIndex) end
        return true
    end

    local big = 1
    if state.flags & FLAG_BIG_HANDS ~= 0 and state.bigScale > 1 then big = state.bigScale end

    local neckX, neckY, neckZ = neck_of(m)
    local body = gore_vr_body(r, m, neckX, neckY, neckZ)

    if vr_remote_pose ~= nil then
        local hands = state.hands & 0xF
        if state.turns ~= nil then
            vr_remote_pose(localIndex, hands | POSE_TURNS,
                body[1], body[2], body[3], body[4], body[5], body[6], big, body[7], body[8], body[9],
                body[10], body[11], body[12], body[13], body[14], body[15],
                body[16], body[17], body[18], body[19], body[20], body[21])
        else
            vr_remote_pose(localIndex, hands,
                body[1], body[2], body[3], body[4], body[5], body[6], big, body[7], body[8], body[9])
        end
    end

    local hatAt = nil
    for hand = 0, 1 do
        local key = globalIndex * 2 + hand
        local valid = state.hands & (hand == 0 and HAND_L_VALID or HAND_R_VALID) ~= 0
        if valid then
            local closed = state.hands & (hand == 0 and HAND_L_CLOSED or HAND_R_CLOSED) ~= 0
            local x = neckX + body[hand * 3 + 1]
            local y = neckY + body[hand * 3 + 2]
            local z = neckZ + body[hand * 3 + 3]
            if vr_remote_pose == nil then
                sGloves[key] = prop_place(sGloves[key], sGloveLook, x, y, z, (closed and GLOVE_CLOSED or GLOVE_OPEN) * big)
            end
            if state.hands & (hand == 0 and HAND_L_HAT or HAND_R_HAT) ~= 0 then
                hatAt = { x, y, z }
            end
        else
            prop_remove(sGloves[key]); sGloves[key] = nil
        end
    end

    if hatAt ~= nil then
        local look = sHatLook[(state.hands >> HAT_SHIFT) & 3]
        sHats[globalIndex] = prop_place(sHats[globalIndex], look, hatAt[1], hatAt[2] + 10, hatAt[3], nil, m.faceAngle.y)
    else
        prop_remove(sHats[globalIndex]); sHats[globalIndex] = nil
    end

    local list = sFx[globalIndex]
    if list == nil then list = {}; sFx[globalIndex] = list end
    local n = 0
    for i = 1, #state.fx do
        local fx = state.fx[i]
        local look = sFxLook[fx[1]]
        if look ~= nil then
            n = n + 1
            list[n] = prop_place(list[n], look, fx[2], fx[3], fx[4])
        end
    end
    for i = #list, n + 1, -1 do
        prop_remove(list[i]); list[i] = nil
    end

    if state.flags & FLAG_POWER_STAR ~= 0 and get_global_timer() % 3 == 0 then
        spawn_non_sync_object(id_bhvSparkleParticleSpawner, E_MODEL_SPARKLES, m.pos.x, m.pos.y + 60, m.pos.z, nil)
    end
    return true
end

local function hat_off(m, r)
    if r.state.hands & (HAND_L_HAT | HAND_R_HAT) == 0 then return end
    m.marioBodyState.capState = MARIO_HAS_DEFAULT_CAP_OFF
end

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex == 0 then return end
    local np = gNetworkPlayers[m.playerIndex]
    if np == nil or not np.connected then return end
    local r = sRemote[np.globalIndex]
    if r == nil or r.age > STALE then return end
    hat_off(m, r)
    face_body(m, r)
end)

local function draw_all()
    for globalIndex, r in pairs(sRemote) do
        r.age = r.age + 1
        local gone = r.age > STALE or not draw_player(globalIndex, r)
        if r.snap ~= nil then
            r.snap = r.snap - 1
            if r.snap <= 0 then r.snap = nil end
        end
        if gone then
            local localIndex = network_local_index_from_global(globalIndex)
            local np = (localIndex ~= nil and localIndex > 0 and localIndex < MAX_PLAYERS) and gNetworkPlayers[localIndex] or nil
            forget(globalIndex, np)
            if np ~= nil and vr_remote_pose ~= nil then vr_remote_pose(localIndex) end
            sRemote[globalIndex] = nil
        end
    end
end

local sHitDamage = { [0] = 1, [1] = 2, [2] = 2, [3] = 3, [4] = 2 }

local function take_hit(attackerGlobal, attackType, yaw)
    local damage = sHitDamage[attackType]
    local localIndex = network_local_index_from_global(attackerGlobal)
    if damage == nil or localIndex == nil or localIndex <= 0 or localIndex >= MAX_PLAYERS then return end
    local attacker, victim = gMarioStates[localIndex], gMarioStates[0]
    if attacker.marioObj == nil or victim.marioObj == nil then return end
    if not gore_true(is_player_active(attacker)) or not gore_true(is_player_active(victim)) then return end
    if victim.invincTimer ~= 0 or victim.hurtCounter ~= 0 then return end
    if victim.action & (ACT_FLAG_INTANGIBLE | ACT_FLAG_INVULNERABLE) ~= 0 then return end
    local vanish = MARIO_VANISH_CAP | MARIO_CAP_ON_HEAD
    if attacker.flags & vanish == vanish or victim.flags & vanish == vanish then return end

    local ao = attacker.marioObj
    local oldFlags, oldYaw, oldDamage = attacker.flags, ao.oFaceAngleYaw, ao.oDamageOrCoinValue
    attacker.flags = attacker.flags | MARIO_PUNCHING
    ao.oFaceAngleYaw = yaw
    if attacker.flags & MARIO_METAL_CAP ~= 0 then damage = damage * 2 end
    ao.oDamageOrCoinValue = damage

    victim.interactObj = ao
    if victim.invincTimer < 3 then victim.invincTimer = 3 end
    take_damage_and_knock_back(victim, ao)
    if attackType == 2 or attackType == 3 then
        if victim.forwardVel < 48 then victim.forwardVel = 48 end
        if victim.vel.y < 28 then victim.vel.y = 28 end
    end
    victim.interactObj = nil

    ao.oDamageOrCoinValue = oldDamage
    ao.oFaceAngleYaw = oldYaw
    attacker.flags = oldFlags
end

local function level_name(level)
    if get_level_name ~= nil and get_level_course_num ~= nil then
        local name = get_level_name(get_level_course_num(level), level, 1)
        if type(name) == "string" and name ~= "" then return name end
    end
    return "level " .. tostring(level)
end

local function on_event(senderGlobal, kind, a)
    local localIndex = network_local_index_from_global(senderGlobal)
    if localIndex == nil or localIndex <= 0 or localIndex >= MAX_PLAYERS then return end
    local np = gNetworkPlayers[localIndex]
    if np == nil or not np.connected then return end
    if kind == EVENT_LEVEL_SELECT then
        if a <= 0 or a >= LEVEL_COUNT then return end
        djui_chat_message_create(tostring(np.name) .. "\\#dcdcdc\\ used the VR Level Select: " .. level_name(a))
        if gOpt ~= nil and gOpt.vr_follow and gNetworkPlayers[0].currLevelNum ~= a then
            warp_to_level(a, 1, 1)
        end
    end
end

local function on_bytes(bytes)
    if type(bytes) ~= "string" or #bytes < 3 or bytes:byte(1) ~= MAGIC then return end
    local kind = bytes:byte(2)
    if kind == PKT_POSE then
        local globalIndex, state = gore_vr_decode_pose(bytes)
        if globalIndex == nil or globalIndex == gNetworkPlayers[0].globalIndex then return end
        local r = sRemote[globalIndex]
        if r == nil then
            sRemote[globalIndex] = { state = state, age = 0 }
        else
            r.state, r.age = state, 0
        end
    elseif kind == PKT_HIT then
        local attacker, victim, attackType, yaw = gore_vr_decode_hit(bytes)
        if attacker == nil then return end
        if sRemote[attacker] ~= nil then sRemote[attacker].snap = SNAP end
        if victim ~= gNetworkPlayers[0].globalIndex then return end
        take_hit(attacker, attackType, yaw)
    elseif kind == PKT_EVENT then
        local sender, what, a = gore_vr_decode_event(bytes)
        if sender == nil or sender == gNetworkPlayers[0].globalIndex then return end
        on_event(sender, what, a)
    end
end

local sSentHands = false

local function read_local()
    local raw = vr_net_state()
    if raw == nil then return nil end
    local m = gMarioStates[0]
    local flags = math.floor(raw[1] or 0)
    local state = { flags = flags & 0xFF, bigScale = raw[2] or 1, hands = 0,
        lx = 0, ly = 0, lz = 0, rx = 0, ry = 0, rz = 0, fx = {} }
    local fromX, fromY, fromZ = m.pos.x, m.pos.y, m.pos.z
    if vr_net_head ~= nil then
        local x, y, z, yaw, pitch, roll, first = vr_net_head()
        if x ~= nil then
            fromX, fromY, fromZ = x, y, z
            state.head = { yaw, pitch, roll }
            state.first = first == true
            state.turned = not state.first
            if vr_net_hands ~= nil then
                local turns = { vr_net_hands() }
                if #turns >= 14 then
                    state.turns = { turns[2], turns[3], turns[4], turns[5], turns[6], turns[7],
                                    turns[9], turns[10], turns[11], turns[12], turns[13], turns[14] }
                end
            end
        end
    end
    if (raw[3] or 0) ~= 0 then
        local how = math.floor(raw[4] or 0)
        state.hands = state.hands | HAND_L_VALID | (how & 1 ~= 0 and HAND_L_CLOSED or 0) | (how & 2 ~= 0 and HAND_L_HAT or 0)
        state.lx, state.ly, state.lz = raw[5] - fromX, raw[6] - fromY, raw[7] - fromZ
    end
    if (raw[8] or 0) ~= 0 then
        local how = math.floor(raw[9] or 0)
        state.hands = state.hands | HAND_R_VALID | (how & 1 ~= 0 and HAND_R_CLOSED or 0) | (how & 2 ~= 0 and HAND_R_HAT or 0)
        state.rx, state.ry, state.rz = raw[10] - fromX, raw[11] - fromY, raw[12] - fromZ
    end
    state.hands = state.hands | (((flags >> 8) & 3) << HAT_SHIFT)
    if gore_vr_local_dead() then
        state.hands, state.head, state.turns, state.first = 0, nil, nil, false
    end
    local count = math.min(math.floor(raw[13] or 0), MAX_FX)
    for i = 0, count - 1 do
        local at = 14 + i * 4
        state.fx[i + 1] = { math.floor(raw[at]), raw[at + 1], raw[at + 2], raw[at + 3] }
    end
    return state
end

local function send_local()
    if vr_net_state == nil then return end
    local alone = network_player_connected_count() <= 1

    local hit = false
    if vr_net_pop_hit ~= nil then
        for _ = 1, 8 do
            local victim, yaw, attackType = vr_net_pop_hit()
            if victim == nil then break end
            hit = true
            if not alone then
                network_send_bytestring(true, gore_vr_encode_hit(gNetworkPlayers[0].globalIndex, victim, attackType, yaw))
            end
        end
    end

    if vr_net_pop_event ~= nil then
        for _ = 1, 8 do
            local kind, a = vr_net_pop_event()
            if kind == nil then break end
            if not alone then
                network_send_bytestring(true, gore_vr_encode_event(gNetworkPlayers[0].globalIndex, kind, a))
            end
        end
    end

    if alone or (not hit and get_global_timer() % SEND_EVERY ~= 0) then return end
    local state = read_local()
    if state == nil then
        if sSentHands then
            sSentHands = false
            network_send_bytestring(true, gore_vr_encode_pose(gNetworkPlayers[0].globalIndex,
                { flags = 0, bigScale = 1, hands = 0, lx = 0, ly = 0, lz = 0, rx = 0, ry = 0, rz = 0, fx = {} }))
        end
        return
    end
    sSentHands = true
    network_send_bytestring(false, gore_vr_encode_pose(gNetworkPlayers[0].globalIndex, state))
end

local DEAD_FRAMES   = 3
local ALIVE_FRAMES  = 5
local DEATH_TO_WARP = 150

local sDeadActions = nil
local sDeadFor = 0
local sAliveFor = ALIVE_FRAMES
local sDiedAt = nil
local sDeathCamera = false

local function dead_actions()
    local t = {}
    for _, action in ipairs({
        ACT_DEATH_ON_BACK, ACT_DEATH_ON_STOMACH, ACT_STANDING_DEATH, ACT_QUICKSAND_DEATH, ACT_ELECTROCUTION,
        ACT_SUFFOCATION, ACT_DROWNING, ACT_WATER_DEATH, ACT_EATEN_BY_BUBBA, ACT_BUBBLED,
    }) do
        t[action] = true
    end
    for _, name in ipairs({ "ACT_GONE", "ACT_NOTHING", "ACT_RAGDOLL", "ACT_NECKSNAP", "ACT_DECAPITATED", "ACT_BITTEN_IN_HALF" }) do
        local action = _G[name]
        if action ~= nil then t[action] = true end
    end
    return t
end

function gore_vr_local_dead()
    local m = gMarioStates[0]
    if m == nil or m.marioObj == nil then return false end
    if m.health <= 0xff then return true end
    if sDeadActions == nil then sDeadActions = dead_actions() end
    if sDeadActions[m.action] then return true end
    if sDiedAt ~= nil then
        if get_global_timer() - sDiedAt < DEATH_TO_WARP then return true end
        sDiedAt = nil
    end
    return false
end

local function death_camera_update()
    if gOpt ~= nil and gOpt.vr_death_cam == false then
        sDeadFor, sAliveFor = 0, ALIVE_FRAMES
    elseif gore_vr_local_dead() then
        sDeadFor, sAliveFor = sDeadFor + 1, 0
    else
        sDeadFor, sAliveFor = 0, sAliveFor + 1
    end
    if sDeadFor >= DEAD_FRAMES then
        sDeathCamera = true
    elseif sAliveFor >= ALIVE_FRAMES then
        sDeathCamera = false
    end
    vr_set_death_camera(sDeathCamera)
end

if vr_set_death_camera ~= nil then
    hook_event(HOOK_UPDATE, death_camera_update)
    hook_event(HOOK_ON_DEATH, function(m)
        if m ~= nil and m.playerIndex == 0 then sDiedAt = get_global_timer() end
    end)
    hook_event(HOOK_ON_WARP, function() sDiedAt = nil end)
end

if sCanPack then
    hook_event(HOOK_ON_PACKET_BYTESTRING_RECEIVE, on_bytes)
    hook_event(HOOK_UPDATE, function()
        send_local()
        draw_all()
    end)
    hook_event(HOOK_ON_PLAYER_DISCONNECTED, function(m)
        local np = gNetworkPlayers[m.playerIndex]
        if np == nil then return end
        local globalIndex = np.globalIndex
        if sRemote[globalIndex] ~= nil or sLooks[globalIndex] ~= nil then
            forget(globalIndex, np)
            sRemote[globalIndex] = nil
        end
    end)
end
