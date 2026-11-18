
local sVanilla = {
    BowlingBallTtmSpeed      = gBehaviorValues.BowlingBallTtmSpeed,
    BowlingBallThiSmallSpeed = gBehaviorValues.BowlingBallThiSmallSpeed,
    KoopaBobAgility          = gBehaviorValues.KoopaBobAgility,
    KoopaThiAgility          = gBehaviorValues.KoopaThiAgility,
    KoopaCatchupAgility      = gBehaviorValues.KoopaCatchupAgility,
    KingBobombHealth         = gBehaviorValues.KingBobombHealth,
    KingBobombFVel           = gBehaviorValues.KingBobombFVel,
    KingBobombYawVel         = gBehaviorValues.KingBobombYawVel,
    pssSlideStarTime         = gLevelValues.pssSlideStarTime,
    metalCapDuration         = gLevelValues.metalCapDuration,
}

GORE_FALL_HEIGHT_STEP    = 50
GORE_FALL_HEIGHT_DEFAULT = 23
GORE_FALL_SPEED_DEFAULT  = 55

GORE_MAX_LIVE_BLOOD = 200
GORE_MAX_LIVE_GIBS  = 400
gGoreBloodCount = 0
gGoreGibCount = 0

local sDefs = {}
local sByKey = {}

local function section(title)
    sDefs[#sDefs + 1] = { section = title }
end

local function opt(scope, key, name, default, min, max, fmt)
    local d = {
        key = key,
        name = name,
        scope = scope,
        kind = (type(default) == "boolean") and "bool" or "int",
        default = default,
        min = min,
        max = max,
        fmt = fmt,
        sync = "o_" .. key,
        store = "opt_" .. key,
        index = nil,
    }
    sDefs[#sDefs + 1] = d
    sByKey[key] = d
    return d
end

section("--- DEATH RULES ---")
opt("host", "onehit_all",     "One-hit mode: ANY damage kills",          false)
opt("host", "enemy_kills",    "Gory insta-kills (Chomp, Piranha, boulders...)", true)
GORE_SMALL_NORMAL, GORE_SMALL_KNOCK, GORE_SMALL_KNOCK_DEAD, GORE_SMALL_SPLAT = 0, 1, 2, 3
local sSmallEnemyLabels = {
    [GORE_SMALL_NORMAL]     = "normal SM64 damage",
    [GORE_SMALL_KNOCK]      = "knock you over, hat off",
    [GORE_SMALL_KNOCK_DEAD] = "knock you over, dead",
    [GORE_SMALL_SPLAT]      = "splatter you",
}
opt("host", "enemy_small",    "Small enemies",                           GORE_SMALL_KNOCK_DEAD, 0, 3, function(v)
    return "Small enemies: " .. (sSmallEnemyLabels[v] or "?")
end)
opt("host", "enemy_fling",    "Bullies & boulders fling you (rag doll)", false)
opt("host", "wiiu_touch_fling", "Let Wii U players tap to fling", false)
opt("host", "enemy_real",     "Every enemy hurts the way it would",      false)
opt("host", "enemy_damage",   "Enemy damage",                            1, 1, 8, function(v)
    return "Enemy damage: x" .. v .. (v == 1 and " (normal)" or "")
end)
GORE_COOLDOWN_NORMAL, GORE_COOLDOWN_UP, GORE_COOLDOWN_NONE = 0, 1, 2
local sCooldownLabels = {
    [GORE_COOLDOWN_NORMAL] = "normal SM64",
    [GORE_COOLDOWN_UP]     = "none once you are up",
    [GORE_COOLDOWN_NONE]   = "none, not even when down",
}
opt("host", "hit_cooldown",   "Damage cooldown",                         GORE_COOLDOWN_NONE, 0, 2, function(v)
    return "Damage cooldown: " .. (sCooldownLabels[v] or "?")
end)
opt("host", "fall_death",     "Falling from high up kills",              true)
opt("host", "fall_height",    "Lethal fall height",                      GORE_FALL_HEIGHT_DEFAULT, 4, 120, function(v)
    return "Lethal fall height: " .. (v * GORE_FALL_HEIGHT_STEP) .. (v == GORE_FALL_HEIGHT_DEFAULT and " (default)" or "")
end)
opt("host", "fall_speed",     "Lethal fall speed",                       GORE_FALL_SPEED_DEFAULT, 20, 75, function(v)
    return "Lethal fall speed: " .. v .. (v == GORE_FALL_SPEED_DEFAULT and " (default)" or "")
end)
opt("host", "fall_hurt",      "Fall injuries",                           0, 0, 30, function(v)
    if v == 0 then return "Fall injuries: off" end
    return "Falls hurt from a drop of: " .. (v * GORE_FALL_HEIGHT_STEP)
end)
opt("host", "water_impact",   "Hitting water from very high up hurts",   false)
opt("host", "lava_death",     "Lava is instant death",                   true)
opt("host", "fire_death",     "Burning to death",                        true)
opt("host", "shock_death",    "Electric shocks kill (electrocution)",    true)
opt("host", "bonk_death",     "Wall-splat when flying into walls",       true)
opt("host", "snow_death",     "Deep snow / sand swallows you",           true)
opt("host", "nukes",          "Explosions are nukes",                    true)
opt("host", "explosion_death", "Explosions kill (flung like a rag doll)", false)
opt("host", "blast_wave",     "Explosions nearby knock you down",        false)
opt("host", "death_blood",    "Always leave blood when you die",         false)
opt("host", "leave_body",     "Violent deaths leave a body (no vanishing)", false)

section("--- WOUNDS ---")
opt("host", "no_healing",     "Wounds don't heal (coins, hearts, stars)", false)
opt("host", "wound_limp",     "Wounded Mario limps (slower when hurt)",  false)
opt("host", "wound_bleed",    "Wounds bleed (blood trail)",              false)
opt("host", "wound_vision",   "Wounded vision (blood on your screen)",   false)

section("--- LIVES & RESPAWN ---")
opt("host", "respawn_in_level", "Respawn in the level you died in",      true)
opt("host", "infinite_lives", "Infinite lives",                          false)

section("--- LEVEL HAZARDS ---")
opt("host", "thirst",         "SSL: heat & thirst",                      true)
opt("host", "freezing",       "SL: freezing to death",                   true)
opt("host", "gas",            "HMC: gas trip",                           true)
opt("host", "fog",            "SL / TTM: fog & darkness",                true)

section("--- ENEMIES ---")
opt("host", "enemy_lunge",    "Goombas lunge at you",                    true)
opt("host", "enemy_fast",     "Aggressive enemies (faster, hunt you)",   true)
opt("host", "enemy_homing",   "Homing boulders, fireballs, bowling balls", true)
opt("host", "enemy_crushers", "Killer Thwomps, Whomps & Grindels",       true)
opt("host", "enemy_chomp",    "Rabid Chain Chomp",                       true)
opt("host", "enemy_birds",    "Klepto & Hoot hunt you",                  true)
opt("host", "bosses_hard",    "Harder bosses & mega throws",             true)
opt("host", "koopa_fast",     "Insane Koopa the Quick & racing penguin", true)

section("--- TRAPS & TROLLS ---")
opt("host", "trap_boxes",     "Killer ! boxes",                          true)
opt("host", "trap_signs",     "Signs turn into Goombas",                 true)
opt("host", "trap_trees",     "Trees fall through the floor",            true)
opt("host", "trap_platforms", "Deadly platforms (fast / exploding)",     true)
opt("host", "trap_items",     "Troll items (hearts, 1-ups, switches)",   true)
opt("host", "timers_hard",    "Brutal timers (3s metal cap, 14s slide)", true)

section("--- MOVEMENT ---")
opt("host", "fast_swim",      "5x swimming speed",                       true)
opt("host", "fast_fly",       "Accelerating flight & cannon shots",      true)
opt("host", "fast_slide",     "Faster slides (PSS / TTM)",               true)
opt("host", "inertia",        "Platform inertia physics",                true)

section("--- BLOOD & GORE ---")
opt("host", "blood_forever",  "Blood stays forever",                     true)
opt("host", "cap_forever",    "Lost caps stay forever",                  true)
opt("host", "body_forever",   "Dead Marios stay forever",                true)
opt("host", "gibs_forever",   "Gibs stay until the level reloads",       false)
opt("host", "enemy_bleed",    "Enemies bleed when you kill them",        false)
opt("local", "blood_save",    "Keep blood between game sessions",        true)
opt("local", "blood_max",     "Max stains per area",                     40, 10, 150, function(v)
    return "Max stains per area (when not unlimited): " .. v
end)
opt("local", "blood_unlimited", "Unlimited stains, caps & bodies (no max)", true)
opt("local", "blood_view",    "View distance for stains",                6, 2, 20, function(v)
    if v >= 20 then return "Stains, caps & bodies shown: all that fit" end
    return "Stains, caps & bodies shown within: " .. (v * 1000)
end)
opt("local", "gib_amount",    "Gib amount",                              10, 0, 10, function(v)
    return "Gib amount: " .. (v * 10) .. "%"
end)
opt("local", "hud_deaths",    "Show death counter",                      true)

section("--- VR PLAYERS ---")
opt("host", "vr_follow",      "VR Level Select takes everybody along",   false)
opt("local", "vr_death_cam",  "VR: third person while you are dead",     true)
opt("local", "vr_hand_height", "VR players' hands: higher / lower",      40, 0, 80, function(v)
    if v == 40 then return "VR players' hands: as measured" end
    if v > 40 then return "VR players' hands: " .. (v - 40) .. " higher" end
    return "VR players' hands: " .. (40 - v) .. " lower"
end)

gOpt = {}

local function sanitize(d, v)
    if d.kind == "bool" then
        if v == nil then return d.default end
        return v == true
    end
    v = tonumber(v)
    if v == nil then return d.default end
    v = math.floor(v)
    if v < d.min then v = d.min end
    if v > d.max then v = d.max end
    return v
end

local function storage_read(d)
    local raw = mod_storage_load(d.store)
    if raw == nil or raw == "" then return d.default end
    if d.kind == "bool" then
        if raw == "1" then return true end
        if raw == "0" then return false end
        return d.default
    end
    return sanitize(d, raw)
end

local function storage_write(d, v)
    if d.kind == "bool" then
        mod_storage_save(d.store, v and "1" or "0")
    else
        mod_storage_save(d.store, tostring(v))
    end
end

do
    local isServer = network_is_server()
    for _, d in ipairs(sDefs) do
        if d.key then
            local v = d.default
            if d.scope == "local" or isServer then
                v = storage_read(d)
            end
            gOpt[d.key] = v
            if d.scope == "host" and (d.key ~= "wiiu_touch_fling" or isServer) then
                gGlobalSyncTable[d.sync] = v
            end
        end
    end

    local stored = mod_storage_load("opt_enemy_small")
    if isServer and (stored == nil or stored == "") and gOpt.enemy_kills == false then
        gOpt.enemy_small = GORE_SMALL_NORMAL
        gGlobalSyncTable.o_enemy_small = GORE_SMALL_NORMAL
    end
end

local function option_label(d, v)
    if d.fmt then return d.fmt(v) end
    return d.name
end

local function menu_refresh(d)
    if d.index == nil or update_mod_menu_element_checkbox == nil then return end
    local v = gOpt[d.key]
    if d.kind == "bool" then
        update_mod_menu_element_checkbox(d.index, v)
    else
        update_mod_menu_element_slider(d.index, v)
        if d.fmt then update_mod_menu_element_name(d.index, option_label(d, v)) end
    end
end

function gore_set_option(key, value)
    local d = sByKey[key]
    if d == nil then return false end
    if d.scope == "host" and not network_is_server() then
        menu_refresh(d)
        return false
    end
    local v = sanitize(d, value)
    gOpt[key] = v
    if d.scope == "host" then
        gGlobalSyncTable[d.sync] = v
    end
    storage_write(d, v)
    menu_refresh(d)
    return true
end

function gore_get_option_default(key)
    local d = sByKey[key]
    return d and d.default
end

local function apply_engine_values()
    local bv, lv = gBehaviorValues, gLevelValues

    if gOpt.enemy_homing then
        bv.BowlingBallTtmSpeed = 40
        bv.BowlingBallThiSmallSpeed = 45
    else
        bv.BowlingBallTtmSpeed = sVanilla.BowlingBallTtmSpeed
        bv.BowlingBallThiSmallSpeed = sVanilla.BowlingBallThiSmallSpeed
    end

    if gOpt.koopa_fast then
        bv.KoopaBobAgility = 20
        bv.KoopaThiAgility = 14
    else
        bv.KoopaBobAgility = sVanilla.KoopaBobAgility
        bv.KoopaThiAgility = sVanilla.KoopaThiAgility
        bv.KoopaCatchupAgility = sVanilla.KoopaCatchupAgility
    end

    if gOpt.bosses_hard then
        bv.KingBobombHealth = 6
    else
        bv.KingBobombHealth = sVanilla.KingBobombHealth
        bv.KingBobombFVel = sVanilla.KingBobombFVel
        bv.KingBobombYawVel = sVanilla.KingBobombYawVel
    end

    if gOpt.timers_hard then
        lv.pssSlideStarTime = 420
        lv.metalCapDuration = 90
    else
        lv.pssSlideStarTime = sVanilla.pssSlideStarTime
        lv.metalCapDuration = sVanilla.metalCapDuration
    end
end

apply_engine_values()

local sFirstRefresh = true
local function refresh_options()
    local changed = sFirstRefresh
    for _, d in ipairs(sDefs) do
        if d.key and d.scope == "host" then
            local v
            if d.key == "wiiu_touch_fling" and network_is_server() then
                v = gOpt[d.key]
                if gGlobalSyncTable[d.sync] ~= v then gGlobalSyncTable[d.sync] = v end
            else
                v = sanitize(d, gGlobalSyncTable[d.sync])
            end
            if gOpt[d.key] ~= v then
                gOpt[d.key] = v
                changed = true
                menu_refresh(d)
            end
        end
    end
    if changed then
        sFirstRefresh = false
        apply_engine_values()
    end
end
hook_event(HOOK_UPDATE, refresh_options)

local function everything(value, keys)
    local t = {}
    for _, k in ipairs(keys) do t[k] = value end
    return t
end

local sWackyKeys = {
    "snow_death", "nukes", "thirst", "freezing", "gas", "fog",
    "enemy_lunge", "enemy_fast", "enemy_homing", "enemy_crushers", "enemy_chomp", "enemy_birds", "bosses_hard", "koopa_fast",
    "trap_boxes", "trap_signs", "trap_trees", "trap_platforms", "trap_items", "timers_hard",
    "fast_swim", "fast_fly", "fast_slide",
}

local sPresetKeeps = {
    respawn_in_level = true, infinite_lives = true,
    blood_forever = true, cap_forever = true, body_forever = true, gibs_forever = true,
    vr_follow = true,
}

local sPresets = {
    realistic = { name = "Realistic SM64", romhack = true, values = (function()
        local t = everything(false, sWackyKeys)
        t.onehit_all = false
        t.enemy_kills = true
        t.enemy_small = GORE_SMALL_KNOCK
        t.enemy_damage = 2
        t.no_healing = true
        t.wound_limp = true
        t.wound_bleed = true
        t.fall_death = true
        t.fall_height = 14
        t.fall_speed = 50
        t.fall_hurt = 8
        t.water_impact = true
        t.explosion_death = true
        t.blast_wave = true
        t.shock_death = true
        t.wound_vision = true
        t.enemy_bleed = true
        t.leave_body = true
        t.enemy_fling = true
        t.enemy_real = true
        t.lava_death = true
        t.fire_death = true
        t.bonk_death = true
        t.death_blood = true
        t.inertia = true
        return t
    end)() },
}

GORE_START_ROMHACK = sPresets.realistic.romhack == true

do
    local values = sPresets.realistic.values
    local isServer = network_is_server()
    for _, d in ipairs(sDefs) do
        if d.key and d.scope == "host" then
            if not sPresetKeeps[d.key] and values[d.key] ~= nil then
                d.default = values[d.key]
            end
            local v = d.default
            if isServer then v = storage_read(d) end
            gOpt[d.key] = v
            if d.key ~= "wiiu_touch_fling" or isServer then gGlobalSyncTable[d.sync] = v end
        end
    end
    local stored = mod_storage_load("opt_enemy_small")
    if isServer and (stored == nil or stored == "") and gOpt.enemy_kills == false then
        gOpt.enemy_small = GORE_SMALL_NORMAL
        gGlobalSyncTable.o_enemy_small = GORE_SMALL_NORMAL
    end
    apply_engine_values()
end

gGoreMenuIndex = {}

function gore_apply_preset(id)
    local preset = sPresets[id]
    if preset == nil then return end
    if not network_is_server() then
        djui_chat_message_create("Option only available for host.")
        return
    end
    for _, d in ipairs(sDefs) do
        if d.key and d.scope == "host" and not sPresetKeeps[d.key] then
            local v = preset.values[d.key]
            if v == nil then v = d.default end
            gore_set_option(d.key, v)
        end
    end
    if preset.romhack ~= nil and gGlobalSyncTable.romhackcompatibility ~= preset.romhack then
        gGlobalSyncTable.romhackcompatibility = preset.romhack
        if gGoreMenuIndex.romhack ~= nil and update_mod_menu_element_checkbox ~= nil then
            update_mod_menu_element_checkbox(gGoreMenuIndex.romhack, preset.romhack)
        end
    end
    apply_engine_values()
    djui_chat_message_create("Preset applied: " .. preset.name .. ". Re-enter the level for everything to take effect.")
end

function gore_build_options_menu()
    local isServer = network_is_server()

    if isServer then
        hook_mod_menu_text("--- PRESET [HOST] ---")
        hook_mod_menu_button("Preset: Realistic SM64", function() gore_apply_preset("realistic") end)
    else
        hook_mod_menu_text("Game rules are chosen by the host.")
    end

    local pendingSection = nil
    for _, d in ipairs(sDefs) do
        if d.section then
            pendingSection = d.section
        elseif d.scope == "local" or isServer then
            if pendingSection then
                hook_mod_menu_text(pendingSection)
                pendingSection = nil
            end
            local key = d.key
            if d.kind == "bool" then
                d.index = hook_mod_menu_checkbox(d.name, gOpt[key], function(_, value)
                    gore_set_option(key, value)
                end)
            else
                d.index = hook_mod_menu_slider(option_label(d, gOpt[key]), gOpt[key], d.min, d.max, function(_, value)
                    gore_set_option(key, value)
                end)
            end
        end
    end

    hook_mod_menu_button("Wipe ALL saved blood, caps & bodies", function()
        if gore_persist_wipe then
            if gore_persist_wipe() then
                djui_chat_message_create("Blood stains, caps and bodies were cleared from your view. The save is the host's.")
            else
                djui_chat_message_create("All saved blood stains, caps and bodies were wiped.")
            end
        end
    end)
end


function gore_true(v)
    return v == true or (v ~= nil and v ~= false and v ~= 0)
end

function gore_gib_bound(n)
    local amount = gOpt.gib_amount
    if amount == nil or amount >= 10 then return n end
    return math.floor((n + 1) * amount / 10) - 1
end

function gore_gated(key, func)
    if func == nil or key == nil then return func end
    return function(o)
        if gOpt[key] then return func(o) end
    end
end

local sFall = {
    air = false,
    act = 0,
    peak = 0,
    vel = 0,
    squish = 0,
    landKb = false,
    ground = nil,
    hurt = false,
}

function gore_fall_is_custom()
    return (not gOpt.fall_death)
        or gOpt.fall_height ~= GORE_FALL_HEIGHT_DEFAULT
        or gOpt.fall_speed ~= GORE_FALL_SPEED_DEFAULT
        or gOpt.fall_hurt > 0
end

function gore_fall_landing_kb()
    return sFall.landKb
end

function gore_fall_hurt()
    return sFall.hurt
end

local sNoFallDamageAfter = {
    [ACT_FLYING] = true,
    [ACT_SHOT_FROM_CANNON] = true,
    [ACT_TWIRLING] = true,
    [ACT_VERTICAL_WIND] = true,
    [ACT_GETTING_BLOWN] = true,
    [ACT_RIDING_SHELL_JUMP] = true,
    [ACT_RIDING_SHELL_FALL] = true,
}

local sAirKnockback = {
    [ACT_HARD_BACKWARD_AIR_KB] = true,
    [ACT_HARD_FORWARD_AIR_KB] = true,
    [ACT_BACKWARD_AIR_KB] = true,
    [ACT_FORWARD_AIR_KB] = true,
}

local sGroundKnockback = {
    [ACT_BACKWARD_GROUND_KB] = true,
    [ACT_FORWARD_GROUND_KB] = true,
    [ACT_SOFT_BACKWARD_GROUND_KB] = true,
    [ACT_SOFT_FORWARD_GROUND_KB] = true,
}

local function is_hard_landing(action)
    return action == ACT_HARD_BACKWARD_GROUND_KB or action == ACT_HARD_FORWARD_GROUND_KB
end

local function fall_wedges(m, wedges)
    if (m.flags & MARIO_CAP_ON_HEAD) == 0 then
        wedges = wedges + (wedges + 1) // 2
    end
    return wedges
end

local function fall_injury(drop)
    local from = gOpt.fall_hurt * GORE_FALL_HEIGHT_STEP
    if gOpt.fall_hurt <= 0 or drop < from then return 0 end
    return math.min(6, 2 + (drop - from) // 150)
end

local WATER_HURT_FACTOR  = 3
local WATER_DEATH_FACTOR = 6
local WATER_MIN_SPEED    = -60

local function water_impact(m, height, speed)
    if speed > WATER_MIN_SPEED or (m.flags & MARIO_METAL_CAP) ~= 0 then return end
    local lethalHeight = gOpt.fall_height * GORE_FALL_HEIGHT_STEP
    if gOpt.fall_death and height >= lethalHeight * WATER_DEATH_FACTOR then
        m.health = 0xff
        m.hurtCounter = 0
        set_camera_shake_from_hit(SHAKE_LARGE_DAMAGE)
        play_character_sound(m, CHAR_SOUND_ATTACKED)
    elseif height >= lethalHeight * WATER_HURT_FACTOR then
        m.hurtCounter = math.min(255, m.hurtCounter + 4 * fall_wedges(m, 3))
        sFall.hurt = true
        set_camera_shake_from_hit(SHAKE_MED_DAMAGE)
        play_character_sound(m, CHAR_SOUND_ATTACKED)
    end
end

local function fall_death_update(m)
    if m.playerIndex ~= 0 then return end
    local s = gStateExtras[0]
    local action = m.action
    local air = (action & ACT_FLAG_AIR) ~= 0

    if sFall.landKb and not is_hard_landing(action) then
        sFall.landKb = false
    end
    if sFall.hurt and m.hurtCounter <= 0 then
        sFall.hurt = false
    end

    if sFall.air and not air then
        local group = action & ACT_GROUP_MASK
        local prev = sFall.act
        local height = sFall.peak - m.pos.y
        local speed = math.min(sFall.vel, m.vel.y)

        sFall.landKb = is_hard_landing(action) and (height > 3000 or not sAirKnockback[prev])
        local drop = math.min((sFall.ground or m.pos.y) - m.pos.y, height)

        if gOpt.water_impact and group == ACT_GROUP_SUBMERGED and m.health > 0xff and not s.isdead
        and (prev & ACT_FLAG_INTANGIBLE) == 0 and (prev & ACT_GROUP_MASK) ~= ACT_GROUP_CUTSCENE
        and not sNoFallDamageAfter[prev] then
            water_impact(m, height, speed)
        end

        local normalLanding = (group == ACT_GROUP_MOVING or group == ACT_GROUP_STATIONARY)
            and (prev & ACT_FLAG_INTANGIBLE) == 0
            and (prev & ACT_GROUP_MASK) ~= ACT_GROUP_CUTSCENE
            and not sNoFallDamageAfter[prev]
            and action ~= ACT_TWIRL_LAND
            and action ~= ACT_RIDING_SHELL_GROUND
            and action ~= ACT_HEAD_STUCK_IN_GROUND
            and action ~= ACT_BUTT_STUCK_IN_GROUND
            and action ~= ACT_FEET_STUCK_IN_GROUND
            and not (m.floor ~= nil and m.floor.type == SURFACE_BURNING)

        if gore_fall_is_custom() and normalLanding and m.health > 0xff and s.splatter == 1 and not s.isdead then
            local lethal = gOpt.fall_death
                and height >= gOpt.fall_height * GORE_FALL_HEIGHT_STEP
                and speed <= -gOpt.fall_speed
                and (height > 3000 or not gore_true(mario_floor_is_slippery(m)))

            if lethal then
                if m.squishTimer == 0 then m.squishTimer = 30 end
                network_play(sSplatter, m.pos, 1, m.playerIndex)
                s.splatterdeath = 1
                s.splatter = 0
            else
                if sFall.squish == 0 and m.squishTimer > 0 and m.squishTimer <= 30 then
                    m.squishTimer = 0
                end
                if m.hurtCounter > 0 and not sAirKnockback[prev] then
                    sFall.hurt = true
                end

                local wedges = fall_injury(drop)
                if wedges > 0 and speed <= -35 and not sAirKnockback[prev]
                and (m.flags & MARIO_METAL_CAP) == 0 and not gore_true(mario_floor_is_slippery(m)) then
                    m.hurtCounter = math.max(m.hurtCounter, math.min(255, 4 * fall_wedges(m, wedges)))
                    sFall.hurt = true
                    set_camera_shake_from_hit(SHAKE_MED_DAMAGE)
                    if not is_hard_landing(action) and not sGroundKnockback[action] then
                        drop_and_set_mario_action(m, m.forwardVel < 0 and ACT_HARD_BACKWARD_GROUND_KB or ACT_HARD_FORWARD_GROUND_KB, 1)
                        sFall.landKb = true
                    end
                end
            end
        end
    end

    sFall.air = air
    if air then
        sFall.act = action
        sFall.peak = m.peakHeight
        sFall.vel = m.vel.y
    else
        sFall.ground = m.pos.y
    end
    sFall.squish = m.squishTimer
end
hook_event(HOOK_MARIO_UPDATE, fall_death_update)
hook_event(HOOK_ON_WARP, function() sFall.ground = nil end)
hook_event(HOOK_ON_LEVEL_INIT, function() sFall.ground = nil end)
