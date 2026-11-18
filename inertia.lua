
local prevPos = {x = 0, y = 0, z = 0}
local inertiaVel = {x = 0, y = 0, z = 0}
local kbAirActions = {
    [ACT_BACKWARD_AIR_KB] = true,
    [ACT_HARD_BACKWARD_AIR_KB] = true,
    [ACT_FORWARD_AIR_KB] = true,
    [ACT_HARD_FORWARD_AIR_KB] = true,
}

local is_mario_grounded = function(m)
    return m.pos.y <= m.floorHeight + 100
end

hook_event(HOOK_BEFORE_PHYS_STEP, function(m)
    if m.playerIndex ~= 0 or not gOpt.inertia then
        return
    end

    if not is_mario_grounded(m) and m.action ~= ACT_GROUND_POUND then
        if kbAirActions[m.action] then
            mario_set_forward_vel(m, m.forwardVel)
        end

        m.vel.x = m.vel.x + inertiaVel.x
        m.vel.z = m.vel.z + inertiaVel.z

        inertiaVel.x = inertiaVel.x * 0.97
        inertiaVel.z = inertiaVel.z * 0.97
    end
end)

hook_event(HOOK_UPDATE, function()
    local m = gMarioStates[0]
    if m.playerIndex ~= 0 then
        return
    end

    if is_mario_grounded(m) then
        prevPos.x = m.pos.x
        prevPos.y = m.pos.y
        prevPos.z = m.pos.z
    end
end)

hook_event(HOOK_ON_SET_MARIO_ACTION, function(m)
    if m.playerIndex ~= 0 then
        return
    end

    if inertiaVel.y < 0 then
        inertiaVel.y = 0
    end

    if is_mario_grounded(m) then
        m.pos.y = m.pos.y + inertiaVel.y
        m.vel.y = m.vel.y + inertiaVel.y
        inertiaVel.y = 0
    end
end)

hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then
        return
    end

    if not gOpt.inertia then
        inertiaVel.x = 0
        inertiaVel.y = 0
        inertiaVel.z = 0
        return
    end

    if is_mario_grounded(m) and m.action & ACT_FLAG_AIR == 0 then
        if m.marioObj.platform then
            inertiaVel.x = m.pos.x - prevPos.x
            inertiaVel.y = (prevPos.y - find_floor_height(m.pos.x, m.pos.y + 100, m.pos.z)) * -1
            inertiaVel.z = m.pos.z - prevPos.z
        else
            inertiaVel.x = 0
            inertiaVel.y = 0
            inertiaVel.z = 0
        end
    end

    if m.action == ACT_BUBBLED then
        inertiaVel.x = 0
        inertiaVel.y = 0
        inertiaVel.z = 0
    end
end)

hook_event(HOOK_ON_WARP, function()
    inertiaVel.x = 0
    inertiaVel.y = 0
    inertiaVel.z = 0
end)

