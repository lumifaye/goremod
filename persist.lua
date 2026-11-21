
local sModels = {
    E_MODEL_BLOOD_SPLATTER,
    E_MODEL_BLOOD_SPLATTER2,
    E_MODEL_BLOOD_SPLATTER_WALL,
    E_MODEL_GOLD_SPLAT,
    E_MODEL_MARIOS_CAP,
    E_MODEL_LUIGIS_CAP,
    E_MODEL_TOADS_CAP,
    E_MODEL_WALUIGIS_CAP,
    E_MODEL_WARIOS_CAP,
    E_MODEL_MARIO,
    E_MODEL_LUIGI,
    E_MODEL_TOAD_PLAYER,
    E_MODEL_WALUIGI,
    E_MODEL_WARIO,
    E_MODEL_HEADLESS_MARIO,
    E_MODEL_HEADLESS_LUIGI,
    E_MODEL_HEADLESS_TOAD,
    E_MODEL_HEADLESS_WALUIGI,
    E_MODEL_HEADLESS_WARIO,
    E_MODEL_TOPLESS_MARIO,
    E_MODEL_TOPLESS_LUIGI,
    E_MODEL_TOPLESS_TOAD,
    E_MODEL_TOPLESS_WALUIGI,
    E_MODEL_TOPLESS_WARIO,
}
local LAST_BLOOD_MODEL = 4
local FIRST_CAP_MODEL = 5
local LAST_CAP_MODEL = 9
local FIRST_BODY_MODEL = 10
local LAST_BODY_MODEL = 24

local function is_cap_model(modelIdx)
    return modelIdx >= FIRST_CAP_MODEL and modelIdx <= LAST_CAP_MODEL
end

local function is_body_model(modelIdx)
    return modelIdx >= FIRST_BODY_MODEL and modelIdx <= LAST_BODY_MODEL
end

local SCAN_INTERVAL   = 10
local SCAN_CROWDED    = 5
local RESTORE_DELAY   = 15
local SAVE_DELAY      = 45
local CHUNK_CHARS     = 1000
local MAX_CAPS        = 10
local MAX_BODIES      = 15

local OBJECT_POOL     = math.floor(tonumber(OBJECT_POOL_CAPACITY) or 1200)
local POOL_RESERVE    = 300
local POOL_PANIC      = 200
local POOL_FLOOR      = 100
local STATIC_AFTER    = 900

local function round(v)
    return math.floor(v + 0.5)
end

local function model_index(o, first, last)
    for i = first, last do
        if gore_true(obj_has_model_extended(o, sModels[i])) then
            return i
        end
    end
    return nil
end

local function count_all_objects()
    if type(gore_allocated_slots) == "function" then return gore_allocated_slots() end
    if obj_get_first == nil or obj_get_next == nil or NUM_OBJ_LISTS == nil then return nil end
    local count = 0
    for list = 0, NUM_OBJ_LISTS - 1 do
        local o = obj_get_first(list)
        while o ~= nil do
            count = count + 1
            o = obj_get_next(o)
        end
    end
    return count
end

local function for_each_object(behaviorId, func)
    if behaviorId == nil then return end
    local o = obj_get_first_with_behavior_id(behaviorId)
    while o ~= nil do
        local nextObj = obj_get_next_with_same_behavior_id(o)
        func(o)
        o = nextObj
    end
end

local sStores = {}

local function store_key(level, area)
    return level .. "_" .. area
end

local function hash_of(model, x, y, z)
    return (model << 57) | (((x // 32) & 0x7FFFF) << 38) | (((y // 32) & 0x7FFFF) << 19) | ((z // 32) & 0x7FFFF)
end

local function entry_hash(e)
    return hash_of(e.m, e.x, e.y, e.z)
end

local CELL = 512

local function cell_add(cells, e)
    local cx, cz = e.x // CELL, e.z // CELL
    local id = cx * 65536 + cz
    local cell = cells[id]
    if cell == nil then
        cell = { x = cx * CELL, z = cz * CELL }
        cells[id] = cell
    end
    cell[#cell + 1] = e
end

local function store_cells(st)
    local cells = st.cells
    if cells == nil then
        cells = {}
        for _, e in ipairs(st.list) do
            cell_add(cells, e)
        end
        st.cells = cells
    end
    return cells
end

local sNet = {
    serial = 0,
}

local function is_guest()
    return network_is_server ~= nil and not network_is_server()
end

local function store_insert(st, e)
    if math.type(e.x) ~= "integer" or math.type(e.y) ~= "integer" or math.type(e.z) ~= "integer" then return false end
    e.h = entry_hash(e)
    if st.set[e.h] then return false end
    sNet.serial = sNet.serial + 1
    e.n = sNet.serial
    st.list[#st.list + 1] = e
    st.set[e.h] = e
    if st.cells ~= nil then cell_add(st.cells, e) end
    return true
end

local function palette_of(np)
    if np == nil then return nil end
    local parts = {}
    for part = 0, PLAYER_PART_MAX - 1 do
        local r = network_player_get_override_palette_color_channel(np, part, 0)
        local g = network_player_get_override_palette_color_channel(np, part, 1)
        local b = network_player_get_override_palette_color_channel(np, part, 2)
        parts[#parts + 1] = (r << 16) | (g << 8) | b
    end
    return table.concat(parts, ",")
end

local function palette_colors(key)
    local colors = {}
    for number in string.gmatch(key, "%d+") do
        local v = math.tointeger(tonumber(number)) or 0
        colors[#colors + 1] = { r = (v >> 16) & 0xFF, g = (v >> 8) & 0xFF, b = v & 0xFF }
    end
    if #colors ~= PLAYER_PART_MAX then return nil end
    return colors
end

local MAX_PALETTES = 0x7FFF
local sPalettes = {}
local sPaletteIndex = {}

local function palette_index(key)
    if key == nil then return 0 end
    local index = sPaletteIndex[key]
    if index == nil then
        local colors = palette_colors(key)
        if colors == nil or #sPalettes >= MAX_PALETTES then return 0 end
        index = #sPalettes + 1
        sPalettes[index] = { key = key, colors = colors }
        sPaletteIndex[key] = index
    end
    return index
end

local function palette_from_fields(f, first)
    for i = first, first + PLAYER_PART_MAX - 1 do
        if f[i] == nil then return nil end
    end
    return table.concat(f, ",", first, first + PLAYER_PART_MAX - 1)
end

local FS_DIR       = "blood/"
local FS_EXT       = ".sav"
local FS_BATCH     = 400
local FS_MAX_SIZE  = MOD_FS_MAX_SIZE or 0x2000000
local FS_MAX_FILES = MOD_FS_MAX_FILES or 0x200
local FS_SAVE_MIN  = 30
local FS_SAVE_MAX  = 900
local FS_SAVE_PER  = 40000

local sFs = {
    state = nil,
    handle = nil,
    dirty = false,
    savedAt = -100000,
    full = false,
    failed = false,
}

local function fs_path(key)
    return FS_DIR .. key .. FS_EXT
end

local function fs_handle()
    if sFs.state == "ok" then return sFs.handle end
    if sFs.state == "off" then return nil end
    sFs.state = "off"
    if mod_fs_get == nil or mod_fs_create == nil or mod_fs_save == nil or mod_fs_get_filename == nil
    or mod_fs_get_file == nil or mod_fs_create_file == nil or mod_fs_delete_file == nil
    or mod_fs_file_read_string == nil or mod_fs_file_write_string == nil or mod_fs_file_erase == nil
    or mod_fs_file_seek == nil or mod_fs_file_rewind == nil or mod_fs_file_is_eof == nil
    or FILE_SEEK_END == nil then
        return nil
    end
    local ok, fs = pcall(function()
        return mod_fs_get() or mod_fs_create()
    end)
    if not ok or fs == nil then return nil end
    sFs.handle = fs
    sFs.state = "ok"
    return fs
end

local function fs_touch()
    sFs.dirty = true
end

local function fs_fail()
    sFs.state = "off"
    sFs.handle = nil
    sFs.dirty = false
    local now = get_global_timer()
    for _, st in pairs(sStores) do
        st.fsCount = 0
        st.fsRewrite = false
        st.dirty = true
        st.dirtyAt = now
    end
    if not sFs.failed then
        sFs.failed = true
        djui_chat_message_create("GORE: the big save file for blood can't be written. Using the small one instead.")
    end
end

local function fs_flush(force)
    if not sFs.dirty then return true end
    local fs = sFs.handle
    if fs == nil then
        sFs.dirty = false
        return false
    end
    local now = get_global_timer()
    if not force then
        local wait = math.min(FS_SAVE_MAX, FS_SAVE_MIN + (fs.totalSize or 0) // FS_SAVE_PER)
        if now >= sFs.savedAt and now - sFs.savedAt < wait then return true end
    end
    sFs.dirty = false
    sFs.savedAt = now
    local ok, saved = pcall(mod_fs_save, fs)
    if ok and saved then return true end
    fs_fail()
    return false
end

local function record_of(e)
    local record = e.m .. "," .. e.x .. "," .. e.y .. "," .. e.z .. "," .. e.p .. "," .. e.w .. "," .. e.r .. "," .. e.s
    if is_body_model(e.m) then
        record = record .. "," .. e.a .. "," .. e.f .. "," .. e.v .. "," .. e.c .. "," .. e.t
        if e.k ~= nil then
            record = record .. "," .. e.k
            if e.g ~= nil then record = record .. "," .. e.g .. "," .. (e.j or 1) end
        end
    elseif is_cap_model(e.m) then
        if e.k ~= nil then
            record = record .. "," .. e.k
            if e.g ~= nil then record = record .. "," .. e.g .. "," .. (e.j or 1) end
        end
    elseif e.l ~= nil then
        record = record .. "," .. e.l
    end
    return record
end

local function records_read(raw, st, filter, added_list)
    local clean = true
    for record in string.gmatch(raw, "[^;%s]+") do
        local f, fields = {}, 0
        for number in string.gmatch(record, "-?%d+") do
            fields = fields + 1
            f[fields] = math.tointeger(tonumber(number))
        end
        local added = false
        local whole = fields >= 8
        for i = 1, whole and 8 or 0 do
            if f[i] == nil then whole = false end
        end
        if whole and sModels[f[1]] ~= nil then
            local e = { m = f[1], x = f[2], y = f[3], z = f[4], p = f[5], w = f[6], r = f[7], s = f[8] }
            if is_body_model(e.m) then
                e.a, e.f, e.v, e.c, e.t = f[9] or -1, f[10] or 0, f[11] or e.s, f[12] or 0, f[13] or 0
                e.k = palette_from_fields(f, 14)
                if e.k ~= nil and f[22] ~= nil and f[22] > 0 then e.g, e.j = f[22], f[23] or 1 end
            elseif is_cap_model(e.m) then
                e.k = palette_from_fields(f, 9)
                if e.k ~= nil and f[17] ~= nil and f[17] > 0 then e.g, e.j = f[17], f[18] or 1 end
            elseif f[9] ~= nil and f[9] > 0 then
                e.l = f[9]
            end
            if filter == nil or filter(st, e) then
                added = store_insert(st, e)
                if added and added_list ~= nil then added_list[#added_list + 1] = e end
            end
        end
        if not added then clean = false end
    end
    return clean
end

local function store_read_disk(key, st)
    st.diskKnown = true

    local fs = fs_handle()
    if fs ~= nil then
        local file = mod_fs_get_file(fs, fs_path(key))
        if file ~= nil then
            mod_fs_file_rewind(file)
            local raw = (not mod_fs_file_is_eof(file)) and mod_fs_file_read_string(file) or nil
            if raw ~= nil and raw ~= "" then
                if records_read(raw, st) then
                    st.fsCount = #st.list
                else
                    st.fsRewrite = true
                    st.dirty = true
                    st.dirtyAt = get_global_timer()
                end
            end
        end
    end

    local chunks = tonumber(mod_storage_load("B" .. key .. "_n")) or 0
    st.chunks = chunks
    st.chunkFrom = #st.list + 1
    for i = 1, chunks do
        local raw = mod_storage_load("B" .. key .. "_" .. i)
        st.written[i] = raw
        if raw ~= nil then
            records_read(raw, st)
        end
    end
    if chunks > 0 and fs ~= nil and not sFs.full then
        st.dirty = true
        st.dirtyAt = get_global_timer()
    end
end

local function store_get(key)
    local st = sStores[key]
    if st == nil then
        st = {
            list = {},
            set = {},
            kill = {},
            dirty = false, dirtyAt = 0,
            fsCount = 0,
            fsRewrite = false,
            chunks = 0,
            chunkFrom = 1,
            written = {},
            diskKnown = false,
            key = key,
        }
        sStores[key] = st
        if gOpt.blood_save and not is_guest() then
            store_read_disk(key, st)
        end
    end
    return st
end

local sStorageFull = false

local function fs_store_write(key, st)
    local fs = fs_handle()
    if fs == nil then
        st.fsCount, st.fsRewrite = 0, false
        return
    end
    local path = fs_path(key)
    local file = mod_fs_get_file(fs, path)
    local count = #st.list

    if count == 0 then
        if file ~= nil and mod_fs_delete_file(fs, path) then
            sFs.full = false
            fs_touch()
        end
        st.fsCount, st.fsRewrite = 0, false
        return
    end

    if file == nil then
        st.fsCount, st.fsRewrite = 0, false
        if sFs.full or (fs.numFiles or 0) >= FS_MAX_FILES then return end
        file = mod_fs_create_file(fs, path, true)
        if file == nil then return end
        fs_touch()
    elseif st.fsRewrite or st.fsCount <= 0 or st.fsCount > count then
        mod_fs_file_rewind(file)
        mod_fs_file_erase(file, FS_MAX_SIZE)
        st.fsCount, st.fsRewrite = 0, false
        sFs.full = false
        fs_touch()
    end

    if st.fsCount < count and not sFs.full then
        mod_fs_file_seek(file, 0, FILE_SEEK_END)
    end
    local batch = FS_BATCH
    while st.fsCount < count and not sFs.full do
        local first = st.fsCount + 1
        local last = math.min(count, first + batch - 1)
        local buffer = {}
        for i = first, last do
            buffer[#buffer + 1] = record_of(st.list[i])
        end
        local text = table.concat(buffer, ";")
        if first > 1 then text = ";" .. text end
        if (fs.totalSize or 0) + #text <= FS_MAX_SIZE and mod_fs_file_write_string(file, text) then
            st.fsCount = last
            fs_touch()
        elseif last > first then
            batch = (last - first + 1) // 2
        else
            sFs.full = true
        end
    end

    if st.fsCount == 0 and mod_fs_delete_file(fs, path) then
        fs_touch()
    end
end

local function chunks_write(key, st, from)
    local chunks = 0
    local failed = false
    local buffer, length = {}, 0

    local function write_chunk()
        local value = table.concat(buffer, ";")
        buffer, length = {}, 0
        if st.written[chunks + 1] ~= value then
            if not mod_storage_save("B" .. key .. "_" .. (chunks + 1), value) then
                failed = true
                if not sStorageFull then
                    sStorageFull = true
                    djui_chat_message_create("GORE: the save file for blood is full. New stains will only last until you close the game.")
                end
                return
            end
            st.written[chunks + 1] = value
        end
        chunks = chunks + 1
    end

    for i = from, #st.list do
        local record = record_of(st.list[i])
        if #buffer > 0 and length + 1 + #record > CHUNK_CHARS then
            write_chunk()
            if failed then break end
        end
        length = length + #record + (#buffer > 0 and 1 or 0)
        buffer[#buffer + 1] = record
    end
    if #buffer > 0 and not failed then
        write_chunk()
    end

    if failed then
        chunks = math.max(chunks, st.chunks)
    else
        for i = chunks + 1, st.chunks do
            mod_storage_remove("B" .. key .. "_" .. i)
            st.written[i] = nil
        end
    end
    if chunks ~= st.chunks then
        if chunks > 0 then
            mod_storage_save("B" .. key .. "_n", tostring(chunks))
        else
            mod_storage_remove("B" .. key .. "_n")
        end
    end
    st.chunks = chunks
    st.chunkFrom = from
end

local function store_write_disk(key, st)
    st.dirty = false
    if not gOpt.blood_save or is_guest() then return end

    if not st.diskKnown then
        st.chunks = tonumber(mod_storage_load("B" .. key .. "_n")) or 0
        st.chunkFrom = 1
        st.diskKnown = true
    end

    fs_store_write(key, st)

    local from = st.fsCount + 1
    if st.chunks > 0 and from > st.chunkFrom and not fs_flush(true) then
        from = 1
    end
    chunks_write(key, st, from)
end

local function store_trim(st)
    if gOpt.blood_unlimited then return end

    local maxBlood = gOpt.blood_max or 40
    local bloods, caps, bodies = 0, 0, 0
    for i = #st.list, 1, -1 do
        local e = st.list[i]
        local over
        if is_cap_model(e.m) then
            caps = caps + 1
            over = caps > MAX_CAPS
        elseif is_body_model(e.m) then
            bodies = bodies + 1
            over = bodies > MAX_BODIES
        else
            bloods = bloods + 1
            over = bloods > maxBlood
        end
        if over then
            table.remove(st.list, i)
            st.set[e.h] = nil
            st.cells = nil
            st.kill[e.h] = true
            st.fsRewrite = true
            st.dirty = true
            st.dirtyAt = get_global_timer()
        end
    end
end

local function store_add(st, e)
    if not store_insert(st, e) then return false end
    st.dirty = true
    st.dirtyAt = get_global_timer()
    e.at = st.dirtyAt
    if sNet.tell ~= nil then sNet.tell(st, e) end
    store_trim(st)
    return true
end

local function flush_stores(olderThan)
    local now = get_global_timer()
    for key, st in pairs(sStores) do
        if st.dirty and (type(olderThan) ~= "number" or now - st.dirtyAt >= olderThan or now < st.dirtyAt) then
            store_write_disk(key, st)
        end
    end
end

local function flush_all()
    flush_stores()
    fs_flush(true)
end

local sScan = {
    key = nil,
    candidates = {},
    needRestore = true,
    readyAt = 0,
    generation = 0,
    bodies = 0,
}

local sCapCandidates = {}

local function entry_from_object(o, modelIdx)
    return {
        m = modelIdx,
        x = round(o.oPosX), y = round(o.oPosY), z = round(o.oPosZ),
        p = round(o.oFaceAnglePitch), w = round(o.oFaceAngleYaw), r = round(o.oFaceAngleRoll),
        s = math.max(1, round(o.header.gfx.scale.x * 100)),
    }
end

local function entry_length(o, e)
    local length = math.max(1, round(o.header.gfx.scale.z * 100))
    if length ~= e.s then e.l = length end
end

local BODY_CAP_OFF = 1
local CAP_OWN_MODEL = 2
local BODY_ANIM_NECKSNAP = -2
local sBodyCustomAnims = { [BODY_ANIM_NECKSNAP] = "MARIO_NECKSNAP" }

local function body_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
end

local function body_loop(o)
    if gMarioStates[0].heldObj ~= nil then
        cur_obj_hide()
    else
        cur_obj_unhide()
    end
end

id_bhvGoreBody = hook_behavior(nil, OBJ_LIST_UNIMPORTANT, true, body_init, body_loop, "bhvGoreBody")

local function spawn_body(e)
    local model = e.m < FIRST_BODY_MODEL + 5 and gore_cs_model(e.g, e.j) or nil
    return spawn_non_sync_object(id_bhvGoreBody, model or sModels[e.m], e.x, e.y, e.z, function(o)
        o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
        o.oOpacity = 255
        o.oBehParams = (palette_index(e.k) << 16) | (e.m << 8) | (e.c & 0xFF)
        o.globalPlayerIndex = gNetworkPlayers[0].globalIndex
        o.oFaceAnglePitch = e.p
        o.oFaceAngleYaw = e.w
        o.oFaceAngleRoll = e.r
        o.oMoveAngleYaw = e.w
        obj_scale_xyz(o, e.s / 100, e.v / 100, e.s / 100)

        local info = o.header.gfx.animInfo
        local frozen = true
        local custom = sBodyCustomAnims[e.a]
        if custom ~= nil then
            smlua_anim_util_set_animation(o, custom)
        else
            local anim = e.a >= 0 and get_mario_vanilla_animation(e.a) or nil
            if anim == nil then
                anim = get_mario_vanilla_animation(MARIO_ANIM_DYING_ON_STOMACH)
                frozen = false
            end
            info.curAnim = anim
            info.animID = e.a
        end
        info.animAccel = 0
        info.animFrame = frozen and e.f or 0
        info.animFrameAccelAssist = info.animFrame << 16
        info.animYTrans = e.t > 0 and e.t or 189
        if frozen then
            o.header.gfx.node.flags = o.header.gfx.node.flags & ~GRAPH_RENDER_HAS_ANIMATION
        end
        o.hookRender = 1
        o.header.gfx.node.hookProcess = 1
        sScan.bodies = sScan.bodies % 0x3FFFFFFF + 1
        o.oBehParams2ndByte = sScan.bodies
    end)
end

local function spawn_stain(e)
    if is_body_model(e.m) then
        return spawn_body(e)
    end
    local ownCap = is_cap_model(e.m) and gore_cs_cap_model(e.g, e.j) or nil
    return spawn_non_sync_object(id_bhvStaticObject, ownCap or sModels[e.m], e.x, e.y, e.z, function(o)
        o.header.gfx.skipInViewCheck = true
        o.oOpacity = 255
        if is_cap_model(e.m) then
            o.globalPlayerIndex = gNetworkPlayers[0].globalIndex
            local palette = palette_index(e.k)
            if palette ~= 0 then
                o.oBehParams = palette << 16
                o.hookRender = 1
                o.header.gfx.node.hookProcess = 1
            end
        end
        o.oBehParams = o.oBehParams | (e.m << 8)
        if ownCap ~= nil then o.oBehParams = o.oBehParams | CAP_OWN_MODEL end
        o.oFaceAnglePitch = e.p
        o.oFaceAngleYaw = e.w
        o.oFaceAngleRoll = e.r
        o.oMoveAngleYaw = e.w
        if e.l ~= nil then
            obj_scale_xyz(o, e.s / 100, 1, e.l / 100)
        else
            obj_scale(o, e.s / 100)
        end
    end)
end

local VIEW_UNIT       = 1000
local VIEW_DEFAULT    = 6
local VIEW_EVERYTHING = 20
local VIEW_FAR        = 200000
local STREAM_RINGS    = 256
local STREAM_STEP     = 128
local STREAM_EVERY    = 30
local STREAM_SPAWNS   = 300
local SYNC_GRACE      = 90

local sStream = {
    key = nil,
    x = 0, y = 0, z = 0,
    at = -100000,
    force = true,
    reach = nil,
    shown = 0, hidden = 0,
}

function gore_persist_shown()
    local st = sStream.key and sStores[sStream.key]
    return sStream.shown, st and #st.list or 0, sStream.hidden
end

local function stream_can_remove(o)
    local syncId = o.oSyncID
    if syncId ~= nil and syncId ~= 0 and o.oTimer < SYNC_GRACE then return false end
    return true
end

local function stream_pass(st, key, now, first, present, shown, shownCount, free, keepBlood, keepCaps, keepBodies)
    local pos = gMarioStates[0].pos
    local vx, vy, vz = pos.x, pos.y, pos.z
    local view = gOpt.blood_view or VIEW_DEFAULT
    local showR = (view >= VIEW_EVERYTHING) and VIEW_FAR or (view * VIEW_UNIT)
    local hideR = showR * 1.1 + 300
    local showR2 = showR * showR

    local searchR = hideR
    if not first and sStream.key == key and sStream.reach ~= nil then
        local mx, my, mz = vx - sStream.x, vy - sStream.y, vz - sStream.z
        searchR = math.min(hideR, sStream.reach * 1.2 + 300 + math.sqrt(mx * mx + my * my + mz * mz))
    end
    local searchR2 = searchR * searchR

    local count, kept, missing = {}, {}, {}
    local seen = {}
    local sqrt, floor = math.sqrt, math.floor
    for _, cell in pairs(store_cells(st)) do
        local x0, z0 = cell.x, cell.z
        local cdx = (vx < x0) and (x0 - vx) or ((vx > x0 + CELL) and (vx - x0 - CELL) or 0)
        local cdz = (vz < z0) and (z0 - vz) or ((vz > z0 + CELL) and (vz - z0 - CELL) or 0)
        if cdx * cdx + cdz * cdz <= searchR2 then
            for i = 1, #cell do
                local e = cell[i]
                local dx, dy, dz = e.x - vx, e.y - vy, e.z - vz
                local d2 = dx * dx + dy * dy + dz * dz
                if d2 <= searchR2 then
                    local h = e.h
                    local o = shown[h]
                    if o ~= nil or not present[h] then
                        local counts = o ~= nil
                        if not counts and d2 <= showR2 then
                            local model = e.m
                            if model <= LAST_BLOOD_MODEL then
                                counts = keepBlood
                            elseif model <= LAST_CAP_MODEL then
                                counts = keepCaps
                            else
                                counts = keepBodies
                            end
                        end
                        if counts then
                            local ring = floor(STREAM_RINGS * sqrt(sqrt(d2) / hideR))
                            if ring >= STREAM_RINGS then ring = STREAM_RINGS - 1 end
                            count[ring] = (count[ring] or 0) + 1
                            local lists = (o ~= nil) and kept or missing
                            local list = lists[ring]
                            if list == nil then
                                list = {}
                                lists[ring] = list
                            end
                            list[#list + 1] = e
                            if o ~= nil then seen[h] = true end
                        end
                    end
                end
            end
        end
    end

    local showCap = math.max(0, free - POOL_RESERVE + shownCount)
    local hideCap = math.max(showCap, free - POOL_PANIC + shownCount)

    local before = 0
    local reach = nil
    local hidden = 0
    local total = shownCount
    local wanted, wantedCount = {}, 0
    for ring = 0, STREAM_RINGS - 1 do
        local n = count[ring]
        if n ~= nil then
            local list = kept[ring]
            local keep = list and #list or 0
            if keep > 0 and before + keep > hideCap then
                local from = math.max(0, hideCap - before)
                for i = #list, from + 1, -1 do
                    local o = shown[list[i].h]
                    if stream_can_remove(o) then
                        obj_mark_for_deletion(o)
                        shown[list[i].h] = nil
                        total = total - 1
                        keep = keep - 1
                    end
                end
            end
            list = missing[ring]
            if list ~= nil then
                local room = math.min(#list, math.max(0, showCap - before - keep))
                for i = 1, room do
                    wantedCount = wantedCount + 1
                    wanted[wantedCount] = list[i]
                end
                hidden = hidden + (#list - room)
            end
            before = before + n
            if reach == nil and before >= hideCap then
                reach = hideR * ((ring + 1) / STREAM_RINGS) ^ 2
            end
        end
    end

    local complete = searchR >= hideR or reach ~= nil
    if complete then
        for h, o in pairs(shown) do
            if not seen[h] and st.set[h] ~= nil and stream_can_remove(o) then
                local e = st.set[h]
                local dx, dy, dz = e.x - vx, e.y - vy, e.z - vz
                if dx * dx + dy * dy + dz * dz > searchR2 then
                    obj_mark_for_deletion(o)
                    total = total - 1
                end
            end
        end
    end

    local spawnNow = math.max(0, free - POOL_FLOOR)
    if not first then spawnNow = math.min(spawnNow, STREAM_SPAWNS) end
    local pending = wantedCount > spawnNow
    for i = 1, math.min(wantedCount, spawnNow) do
        local e = wanted[i]
        local copy = spawn_stain(e)
        if copy == nil then
            pending = true
            break
        end
        shown[e.h] = copy
        present[e.h] = true
        total = total + 1
    end

    sStream.key = key
    sStream.x, sStream.y, sStream.z = vx, vy, vz
    sStream.at = now
    sStream.reach = reach
    sStream.force = pending or not complete
    sStream.shown, sStream.hidden = total, hidden
end

local function request_restore(delay)
    sScan.generation = sScan.generation + 1
    sScan.needRestore = true
    sScan.candidates = {}
    sScan.readyAt = get_global_timer() + (delay or RESTORE_DELAY)
end

local function scan_level()
    local m = gMarioStates[0]
    local np = gNetworkPlayers[0]
    if m.marioObj == nil or not np.currAreaSyncValid then return end

    local now = get_global_timer()
    local key = store_key(np.currLevelNum, np.currAreaIndex)
    if key ~= sScan.key then
        local oldStore = sScan.key and sStores[sScan.key]
        if oldStore and oldStore.dirty then
            store_write_disk(sScan.key, oldStore)
        end
        sScan.key = key
        request_restore()
        if sNet.ask ~= nil then sNet.ask(key) end
    end

    gGoreBloodCount = obj_count_objects_with_behavior_id(id_bhvSquishblood)
    gGoreGibCount = obj_count_objects_with_behavior_id(id_bhvGib)

    local keepBlood = gOpt.blood_forever
    local keepCaps = gOpt.cap_forever
    local keepBodies = gOpt.body_forever
    if not keepBlood and not keepCaps and not keepBodies then
        sScan.candidates = {}
        sCapCandidates = {}
        return
    end

    local st = store_get(key)
    if #st.list > (gOpt.blood_max or 40) + MAX_CAPS + MAX_BODIES then
        store_trim(st)
    end
    local kill = st.kill
    st.kill = {}
    local present = {}
    local shown = {}
    local shownCount = 0
    local candidates = sScan.candidates
    local nextCandidates = {}

    local freeSlots = nil
    local function free_slots()
        if freeSlots == nil then
            local used = count_all_objects()
            if used == nil then
                used = 400 + gGoreBloodCount + gGoreGibCount + obj_count_objects_with_behavior_id(id_bhvGoreBody)
                    + obj_count_objects_with_behavior_id(id_bhvStaticObject)
            end
            used = math.max(used, gGoreBloodCount + gGoreGibCount)
            freeSlots = OBJECT_POOL - used
        end
        return freeSlots
    end

    local unlimited = gOpt.blood_unlimited
    local conversions = 0

    local function visit(o, firstModel, lastModel, isDecoration, modelIdx)
        if o.activeFlags == ACTIVE_FLAG_DEACTIVATED then return end
        if modelIdx == nil then
            modelIdx = model_index(o, firstModel, lastModel)
        elseif modelIdx < firstModel or modelIdx > lastModel then
            modelIdx = nil
        end
        if modelIdx == nil then return end
        local x, y, z = round(o.oPosX), round(o.oPosY), round(o.oPosZ)
        if math.type(x) ~= "integer" or math.type(y) ~= "integer" or math.type(z) ~= "integer" then return end
        local h = hash_of(modelIdx, x, y, z)
        if kill[h] then
            obj_mark_for_deletion(o)
            return
        end
        present[h] = true
        if isDecoration then
            if shown[h] == nil then shownCount = shownCount + 1 end
            shown[h] = o
        elseif unlimited and conversions < 20 and st.set[h] ~= nil and o.oTimer > STATIC_AFTER
        and o.oFloor ~= nil and o.oFloor.object == nil and free_slots() > POOL_PANIC then
            local copy = spawn_stain(st.set[h])
            if copy ~= nil then
                obj_mark_for_deletion(o)
                conversions = conversions + 1
                shown[h] = copy
                shownCount = shownCount + 1
                freeSlots = freeSlots - 1
            end
        end
        if keepBlood and modelIdx <= LAST_BLOOD_MODEL and st.set[h] == nil then
            if candidates[h] then
                local e = entry_from_object(o, modelIdx)
                entry_length(o, e)
                store_add(st, e)
            else
                nextCandidates[h] = true
            end
        end
    end

    for_each_object(id_bhvSquishblood, function(o) visit(o, 1, LAST_BLOOD_MODEL) end)
    for_each_object(id_bhvStaticObject, function(o)
        local tagged = (o.oBehParams >> 8) & 0xFF
        if tagged < 1 or tagged > LAST_CAP_MODEL then
            tagged = nil
        elseif is_cap_model(tagged) and (o.oBehParams & CAP_OWN_MODEL) ~= 0 then
        elseif not gore_true(obj_has_model_extended(o, sModels[tagged])) then
            tagged = nil
        end
        visit(o, 1, LAST_CAP_MODEL, true, tagged)
    end)
    for_each_object(id_bhvGoreBody, function(o) visit(o, FIRST_BODY_MODEL, LAST_BODY_MODEL, true, (o.oBehParams >> 8) & 0xFF) end)
    sScan.candidates = nextCandidates

    if keepCaps then
        local seenOwners = {}
        for_each_object(id_bhvNormalCap, function(o)
            if o.activeFlags == ACTIVE_FLAG_DEACTIVATED then return end
            local globalIndex = o.globalPlayerIndex
            seenOwners[globalIndex] = true

            local e = entry_from_object(o, model_index(o, FIRST_CAP_MODEL, LAST_CAP_MODEL) or FIRST_CAP_MODEL)
            e.p, e.r = 0, 0
            local owner = network_player_from_global_index(globalIndex)
            e.k = palette_of(owner)
            if owner ~= nil then e.g, e.j = gore_cs_of_player(owner.localIndex) end
            if o.hookRender == 0 then o.hookRender = 1 end
            local floor = collision_find_floor(e.x, e.y + 80, e.z)
            if floor ~= nil and floor.type ~= SURFACE_DEATH_PLANE then
                e.y = round(find_floor_height(e.x, e.y + 80, e.z))
                sCapCandidates[globalIndex] = { key = key, gen = sScan.generation, e = e }
            else
                sCapCandidates[globalIndex] = nil
            end
        end)

        for globalIndex, candidate in pairs(sCapCandidates) do
            if candidate.key ~= key or not seenOwners[globalIndex] then
                sCapCandidates[globalIndex] = nil
                if candidate.key ~= key or candidate.gen ~= sScan.generation then
                    local capStore = store_get(candidate.key)
                    if store_add(capStore, candidate.e) and candidate.key == key and not sScan.needRestore then
                        sScan.needRestore = true
                        sScan.readyAt = now
                    end
                end
            end
        end
    else
        sCapCandidates = {}
    end

    if not (sScan.needRestore and now < sScan.readyAt) then
        local first = sScan.needRestore
        local pos = m.pos
        local dx, dy, dz = pos.x - sStream.x, pos.y - sStream.y, pos.z - sStream.z
        if first or sStream.force or sStream.key ~= key
        or now - sStream.at >= STREAM_EVERY or now < sStream.at
        or dx * dx + dy * dy + dz * dz >= STREAM_STEP * STREAM_STEP
        or (shownCount > 0 and free_slots() < POOL_PANIC) then
            sScan.needRestore = false
            stream_pass(st, key, now, first, present, shown, shownCount, free_slots(), keepBlood, keepCaps, keepBodies)
        end
    end

    if st.dirty and now - st.dirtyAt >= SAVE_DELAY then
        store_write_disk(key, st)
    end
end

local function save_pending()
    if not gOpt.blood_save then return end
    flush_stores(SAVE_DELAY)
    fs_flush(false)
end

local sScanTimer = 0
hook_event(HOOK_UPDATE, function()
    sScanTimer = sScanTimer + 1
    local interval = SCAN_INTERVAL
    if sStream.reach ~= nil and sScanTimer >= SCAN_CROWDED then
        local pos = gMarioStates[0].pos
        local dx, dy, dz = pos.x - sStream.x, pos.y - sStream.y, pos.z - sStream.z
        if dx * dx + dy * dy + dz * dz >= STREAM_STEP * STREAM_STEP then
            interval = SCAN_CROWDED
        end
    end
    if sScanTimer >= interval then
        sScanTimer = 0
        scan_level()
        save_pending()
    end
end)

hook_event(HOOK_ON_SYNC_VALID, function()
    request_restore()
    if sNet.ask ~= nil and sScan.key ~= nil then
        local np = gNetworkPlayers[0]
        if store_key(np.currLevelNum, np.currAreaIndex) == sScan.key then sNet.ask(sScan.key) end
    end
end)
if HOOK_ON_EXIT ~= nil then
    hook_event(HOOK_ON_EXIT, flush_all)
end

function gore_persist_wipe(told)
    sStores = {}
    sCapCandidates = {}
    sScan.candidates = {}
    sScan.needRestore = false
    sStorageFull = false
    if sNet.wiped ~= nil then sNet.wiped(told) end

    local all = (not is_guest()) and mod_storage_load_all() or nil
    if all ~= nil then
        for key, _ in pairs(all) do
            if type(key) == "string" and string.match(key, "^B%d+_%d+_") then
                mod_storage_remove(key)
            end
        end
    end

    local fs = (not is_guest()) and fs_handle() or nil
    if fs ~= nil then
        local names = {}
        for i = 0, (fs.numFiles or 0) - 1 do
            local name = mod_fs_get_filename(fs, i)
            if type(name) == "string" and string.sub(name, 1, #FS_DIR) == FS_DIR then
                names[#names + 1] = name
            end
        end
        for _, name in ipairs(names) do
            mod_fs_delete_file(fs, name)
        end
        sFs.full = false
        if #names > 0 then
            fs_touch()
            fs_flush(true)
        end
    end

    for_each_object(id_bhvSquishblood, function(o) obj_mark_for_deletion(o) end)
    for_each_object(id_bhvStaticObject, function(o)
        if model_index(o, 1, LAST_CAP_MODEL) ~= nil then
            obj_mark_for_deletion(o)
        end
    end)
    for_each_object(id_bhvGoreBody, function(o) obj_mark_for_deletion(o) end)
    gore_bodies_forget()
    return is_guest()
end

do
local PKT_ASK, PKT_DATA, PKT_TELL, PKT_WIPE = 20, 21, 22, 23
local PACK_CHARS    = 250
local PACK_STRINGS  = 8
local SEND_PER_FRAME = 2
local ASK_AGAIN     = 150
local MAX_BLOOD     = 20000
local NEAR          = 150
local TELL_EVERY    = 30
local TELL_WINDOW   = 300
local TELL_MAX      = 40
local TOLD_RECENTLY = 600

local sOut = {}
local sAsked = {}
local sTell = {}
local sTellAt = 0
local sTold = {}

local function host_index()
    local i = network_local_index_from_global(0)
    if i == nil or i <= 0 or i >= MAX_PLAYERS then return nil end
    local np = gNetworkPlayers[i]
    if np == nil or not np.connected then return nil end
    return i
end

local function valid_key(key)
    return type(key) == "string" and #key <= 24 and string.match(key, "^%d+_%d+$") ~= nil
end

local function kind_of(e)
    if is_body_model(e.m) then return 2 end
    if is_cap_model(e.m) then return 1 end
    return 0
end

local function near_one(st, e, kind, pick)
    for i = #st.list, 1, -1 do
        local b = st.list[i]
        if b.at ~= nil and b.k == e.k and kind_of(b) == kind and pick(b) then
            local dx, dy, dz = b.x - e.x, b.y - e.y, b.z - e.z
            if dx * dx + dy * dy + dz * dz <= NEAR * NEAR then return b end
        end
    end
    return nil
end

local function pack(packet, list, i, as_record)
    local strings = 0
    while i <= #list and strings < PACK_STRINGS do
        local buffer, length = {}, 0
        while i <= #list do
            local record = as_record and list[i] or record_of(list[i])
            if #record > PACK_CHARS then
                i = i + 1
            elseif #buffer > 0 and length + 1 + #record > PACK_CHARS then
                break
            else
                length = length + #record + (#buffer > 0 and 1 or 0)
                buffer[#buffer + 1] = record
                i = i + 1
            end
        end
        if #buffer > 0 then
            strings = strings + 1
            packet[strings] = table.concat(buffer, ";")
        end
    end
    return i
end

local function show_soon(key)
    if key == sScan.key and not sScan.needRestore then
        sScan.needRestore = true
        sScan.readyAt = get_global_timer()
    end
end


sNet.ask = function(key)
    if not is_guest() or not valid_key(key) then return end
    local now = get_global_timer()
    local last = sAsked[key]
    if last ~= nil and now >= last and now - last < ASK_AGAIN then return end
    local host = host_index()
    if host == nil then return end
    sAsked[key] = now
    local st = store_get(key)
    network_send_to(host, true, {
        type = PKT_ASK, key = key, after = st.hostSerial or 0,
        g = gNetworkPlayers[0].globalIndex,
        max = (not gOpt.blood_unlimited) and (gOpt.blood_max or 40) or 0,
    })
end

sNet.tell = function(st, e)
    if st.key == nil or not is_guest() then return end
    local host = host_index()
    if host == nil or gore_true(is_player_active(gMarioStates[host])) then return end
    local queue = sTell[st.key]
    if queue == nil then
        queue = {}
        sTell[st.key] = queue
    end
    if #queue < 2000 then queue[#queue + 1] = record_of(e) end
end

local function tell_update(now)
    if now >= sTellAt and now - sTellAt < TELL_EVERY then return end
    local key, queue = next(sTell)
    if key == nil then return end
    local host = host_index()
    if host == nil then return end
    sTellAt = now
    local packet = { type = PKT_TELL, key = key, g = gNetworkPlayers[0].globalIndex }
    local i = pack(packet, queue, 1, true)
    if i > #queue then
        sTell[key] = nil
    else
        local rest = {}
        for j = i, #queue do rest[#rest + 1] = queue[j] end
        sTell[key] = rest
    end
    if packet[1] ~= nil then network_send_to(host, true, packet) end
end

local function on_data(data)
    if not is_guest() or not valid_key(data.key) then return end
    local st = store_get(data.key)
    local added = {}
    local function filter(_, e)
        local kind = kind_of(e)
        if kind == 0 then return true end
        local mine = near_one(st, e, kind, function(b) return not b.paired end)
        if mine == nil then return true end
        mine.paired = true
        return false
    end
    for i = 1, PACK_STRINGS do
        local raw = data[i]
        if type(raw) == "string" then records_read(raw, st, filter, added) end
    end
    if #added > 0 then
        store_trim(st)
        show_soon(data.key)
    end
    local done = math.tointeger(data.done)
    if done ~= nil and done > (st.hostSerial or 0) then st.hostSerial = done end
end


local function on_ask(data)
    if is_guest() or not valid_key(data.key) then return end
    local g, after, max = math.tointeger(data.g), math.tointeger(data.after) or 0, math.tointeger(data.max) or 0
    if g == nil or g <= 0 or g >= MAX_PLAYERS then return end
    local to = network_local_index_from_global(g)
    if to == nil or to <= 0 or to >= MAX_PLAYERS or not gNetworkPlayers[to].connected then return end

    local st = store_get(data.key)
    local first, blood = {}, {}
    for _, e in ipairs(st.list) do
        if e.n ~= nil and e.n > after then
            if kind_of(e) ~= 0 then first[#first + 1] = e else blood[#blood + 1] = e end
        end
    end
    local limit = (max > 0 and max < MAX_BLOOD) and max or MAX_BLOOD
    for i = math.max(1, #blood - limit + 1), #blood do
        first[#first + 1] = blood[i]
    end
    sOut[to] = { key = data.key, list = first, i = 1, top = sNet.serial }
end

local function send_update()
    local waiting = 0
    for _ in pairs(sOut) do waiting = waiting + 1 end
    local each = math.max(1, SEND_PER_FRAME // waiting)
    for to, out in pairs(sOut) do
        local np = gNetworkPlayers[to]
        if np == nil or not np.connected then
            sOut[to] = nil
        else
            for _ = 1, each do
                local packet = { type = PKT_DATA, key = out.key }
                out.i = pack(packet, out.list, out.i)
                local done = out.i > #out.list
                if done then
                    packet.done = out.top
                    sOut[to] = nil
                end
                network_send_to(to, true, packet)
                if done then break end
            end
        end
    end
end

local function on_tell(data)
    if is_guest() or not valid_key(data.key) then return end
    local g = math.tointeger(data.g)
    if g == nil or g <= 0 or g >= MAX_PLAYERS then return end
    local now = get_global_timer()
    local told = sTold[g]
    if told == nil or now < told.at or now - told.at >= TELL_WINDOW then
        told = { at = now, n = 0 }
        sTold[g] = told
    end
    told.n = told.n + 1
    if told.n > TELL_MAX then return end

    local st = store_get(data.key)
    local added = {}
    local function filter(_, e)
        local kind = kind_of(e)
        if kind == 0 then return true end
        return near_one(st, e, kind, function(b) return now >= b.at and now - b.at < TOLD_RECENTLY end) == nil
    end
    for i = 1, PACK_STRINGS do
        local raw = data[i]
        if type(raw) == "string" then records_read(raw, st, filter, added) end
    end
    if #added == 0 then return end
    for _, e in ipairs(added) do e.at = now end
    st.dirty = true
    st.dirtyAt = now
    store_trim(st)
    show_soon(data.key)
end


sNet.wiped = function(told)
    sOut, sAsked, sTell = {}, {}, {}
    if not told and not is_guest() then
        network_send(true, { type = PKT_WIPE })
    end
end

hook_event(HOOK_ON_PACKET_RECEIVE, function(data)
    if type(data) ~= "table" then return end
    local kind = data.type
    if kind == PKT_ASK then
        on_ask(data)
    elseif kind == PKT_DATA then
        on_data(data)
    elseif kind == PKT_TELL then
        on_tell(data)
    elseif kind == PKT_WIPE then
        if is_guest() then
            gore_persist_wipe(true)
            djui_chat_message_create("GORE: the host wiped all blood stains, caps and bodies.")
        end
    end
end)

hook_event(HOOK_UPDATE, function()
    if is_guest() then
        tell_update(get_global_timer())
    elseif next(sOut) ~= nil then
        send_update()
    end
end)
end

local sBodyActions = {
    [ACT_DEATH_ON_BACK] = true,
    [ACT_DEATH_ON_STOMACH] = true,
    [ACT_STANDING_DEATH] = true,
    [ACT_ELECTROCUTION] = true,
    [ACT_SUFFOCATION] = true,
    [ACT_DROWNING] = true,
    [ACT_WATER_DEATH] = true,
    [ACT_DECAPITATED] = true,
    [ACT_BITTEN_IN_HALF] = true,
    [ACT_NECKSNAP] = true,
    [ACT_NOTHING] = true,
}

local sBodySnaps = {}
local sBodyCrushed = {}

function gore_bodies_forget()
    sBodySnaps = {}
    sBodyCrushed = {}
end

local function clamp_int(v, lo, hi)
    v = round(v)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

local function body_visible(m)
    local o = m.marioObj
    if o == nil then return false end
    local flags = o.header.gfx.node.flags
    return (flags & GRAPH_RENDER_ACTIVE) ~= 0 and (flags & GRAPH_RENDER_INVISIBLE) == 0
end

local function body_lies(m)
    if not sBodyActions[m.action] or not body_visible(m) then return false end
    if m.action == ACT_NOTHING and m.health > 0xff then return false end
    if m.floor ~= nil and (m.floor.type == SURFACE_DEATH_PLANE or m.floor.type == SURFACE_BURNING)
    and m.pos.y - m.floorHeight < 100 then
        return false
    end
    return m.pos.y - m.floorHeight < 40 or m.pos.y < m.waterLevel
end

local function body_entry(m)
    local o = m.marioObj
    local gfx = o.header.gfx
    local info = gfx.animInfo

    local kind = 0
    local models = GoreHMApi ~= nil and GoreHMApi.get_char_models(m) or nil
    if models ~= nil then
        if models.headless ~= nil and gore_true(obj_has_model_extended(o, models.headless)) then
            kind = 1
        elseif models.topless ~= nil and gore_true(obj_has_model_extended(o, models.topless)) then
            kind = 2
        end
    end
    local csCharacter, csCostume = nil, nil
    if kind == 0 then csCharacter, csCostume = gore_cs_of_player(m.playerIndex) end
    local character = m.character ~= nil and m.character.type or CT_MARIO
    if character < CT_MARIO or character > CT_WARIO then character = CT_MARIO end

    local anim = info.animID
    if m.action == ACT_NECKSNAP then anim = BODY_ANIM_NECKSNAP end

    return {
        m = FIRST_BODY_MODEL + 5 * kind + character,
        x = round(gfx.pos.x), y = round(gfx.pos.y), z = round(gfx.pos.z),
        p = round(gfx.angle.x), w = round(gfx.angle.y), r = round(gfx.angle.z),
        s = clamp_int(gfx.scale.x * 100, 5, 400),
        v = clamp_int(gfx.scale.y * 100, 5, 400),
        a = anim,
        f = math.max(0, info.animFrame),
        c = ((m.flags & MARIO_CAP_ON_HEAD) == 0) and BODY_CAP_OFF or 0,
        t = math.max(0, info.animYTrans),
        k = palette_of(gNetworkPlayers[m.playerIndex]),
        g = csCharacter, j = csCostume,
    }
end

local function body_ground(m)
    local o = m.floor ~= nil and m.pos.y - m.floorHeight < 40 and m.floor.object or nil
    if o == nil then return nil end
    return { o = o, x = o.oPosX, y = o.oPosY, z = o.oPosZ, p = o.oFaceAnglePitch, w = o.oFaceAngleYaw, r = o.oFaceAngleRoll }
end

local function body_snap(m, key, old)
    local snap = { key = key, e = body_entry(m), ground = body_ground(m), adrift = old ~= nil and old.adrift or false }
    local g, was = snap.ground, old ~= nil and old.ground or nil
    if g ~= nil and was ~= nil and g.o == was.o
    and (g.x ~= was.x or g.y ~= was.y or g.z ~= was.z or g.p ~= was.p or g.w ~= was.w or g.r ~= was.r) then
        snap.adrift = true
    end
    return snap
end

local function body_commit(snap)
    if snap.adrift then return end
    local st = store_get(snap.key)
    if store_add(st, snap.e) and snap.key == sScan.key and not sScan.needRestore then
        sScan.needRestore = true
        sScan.readyAt = get_global_timer()
    end
end

hook_event(HOOK_MARIO_UPDATE, function(m)
    local i = m.playerIndex
    if not gOpt.body_forever then
        sBodySnaps[i] = nil
        sBodyCrushed[i] = nil
        return
    end

    local np = gNetworkPlayers[0]
    local key = store_key(np.currLevelNum, np.currAreaIndex)
    local here = (i == 0) or gore_true(is_player_active(m))

    local snap = sBodySnaps[i]
    if snap ~= nil and (not here or snap.key ~= key) then
        sBodySnaps[i] = nil
        body_commit(snap)
        snap = nil
    end

    if here and np.currAreaSyncValid and m.action == ACT_SQUISHED and body_visible(m) then
        sBodyCrushed[i] = body_snap(m, key, sBodyCrushed[i])
    elseif sBodyCrushed[i] ~= nil then
        local crushed = sBodyCrushed[i]
        sBodyCrushed[i] = nil
        if here and crushed.key == key and m.action == ACT_DISAPPEARED and m.health <= 0xff and snap == nil then
            body_commit(crushed)
        end
    end

    if here and np.currAreaSyncValid and body_lies(m) then
        sBodySnaps[i] = body_snap(m, key, snap)
        return
    end

    if snap == nil then return end
    if sBodyActions[m.action] then return end
    sBodySnaps[i] = nil
    body_commit(snap)
end)

hook_event(HOOK_UPDATE, function()
    for i, snap in pairs(sBodySnaps) do
        if i ~= 0 and not gore_true(is_player_active(gMarioStates[i])) then
            sBodySnaps[i] = nil
            body_commit(snap)
        end
    end
end)

do
local sLive = nil
local sShownKey = nil
local sLiveColors = { key = nil, colors = nil }

local function look_show_palette(key, colors)
    if key == sShownKey or colors == nil then return end
    local np = gNetworkPlayers[0]
    for part = 0, PLAYER_PART_MAX - 1 do
        network_player_set_override_palette_color(np, part, colors[part + 1])
    end
    sShownKey = key
end

local function look_borrow()
    local live = sLive
    if live == nil then
        local key = palette_of(gNetworkPlayers[0])
        if key ~= sLiveColors.key then
            sLiveColors.key = key
            sLiveColors.colors = palette_colors(key)
        end
        live = { key = key, colors = sLiveColors.colors, body = false }
        sLive = live
        sShownKey = key
    end
    return live
end

local sBodyHair = {}
local sBodyHairCount = 0

local function hair_prune(now)
    for id, hair in pairs(sBodyHair) do
        if now - hair.seen > 90 or hair.seen > now then
            sBodyHair[id] = nil
            sBodyHairCount = sBodyHairCount - 1
        end
    end
end

local function hair_borrow(live, o)
    local all = _G.physBoneMem
    if type(all) ~= "table" or type(all[0]) ~= "table" then return end
    local now = get_global_timer()
    local id = o.oBehParams2ndByte
    local hair = sBodyHair[id]
    if hair == nil then
        if sBodyHairCount >= 64 then hair_prune(now) end
        hair = { seen = now, mem = {}, fresh = true }
        sBodyHair[id] = hair
        sBodyHairCount = sBodyHairCount + 1
    end
    hair.seen = now
    if hair.fresh and next(hair.mem) ~= nil then
        hair.fresh = nil
        for _, bone in pairs(hair.mem) do
            if type(bone) == "table" then
                if type(bone.yaw) == "number" then bone.yaw = 0 end
                if type(bone.pitch) == "number" then bone.pitch = 0 end
            end
        end
    end
    if live.hairOf == nil then
        live.hairOf, live.hair = all, all[0]
    end
    all[0] = hair.mem
end

local function look_restore()
    local live = sLive
    if live == nil then return end
    sLive = nil
    look_show_palette(live.key, live.colors)
    sShownKey = nil
    if live.hairOf ~= nil then
        live.hairOf[0] = live.hair
    end
    if not live.body then return end
    local b = gMarioStates[0].marioBodyState
    if b == nil then return end
    b.eyeState, b.capState, b.handState = live.eyes, live.cap, live.hands
    b.modelState, b.punchState, b.action = live.model, live.punch, live.action
    b.allowPartRotation = live.parts
    b.torsoAngle.x, b.torsoAngle.y, b.torsoAngle.z = live.tx, live.ty, live.tz
    b.headAngle.x, b.headAngle.y, b.headAngle.z = live.hx, live.hy, live.hz
end

local function look_borrow_palette(live, index)
    local palette = sPalettes[index]
    if palette ~= nil then
        look_show_palette(palette.key, palette.colors)
    else
        look_show_palette(live.key, live.colors)
    end
end

hook_event(HOOK_ON_OBJECT_RENDER, function(o)
    if gore_true(obj_has_behavior_id(o, id_bhvGoreBody)) then
        local b = gMarioStates[0].marioBodyState
        if b == nil then return end
        local live = look_borrow()
        if not live.body then
            live.body = true
            live.eyes, live.cap, live.hands = b.eyeState, b.capState, b.handState
            live.model, live.punch, live.action = b.modelState, b.punchState, b.action
            live.parts = b.allowPartRotation
            live.tx, live.ty, live.tz = b.torsoAngle.x, b.torsoAngle.y, b.torsoAngle.z
            live.hx, live.hy, live.hz = b.headAngle.x, b.headAngle.y, b.headAngle.z
        end
        look_borrow_palette(live, (o.oBehParams >> 16) & MAX_PALETTES)
        hair_borrow(live, o)
        b.eyeState = MARIO_EYES_DEAD
        b.capState = ((o.oBehParams & BODY_CAP_OFF) ~= 0) and MARIO_HAS_DEFAULT_CAP_OFF or MARIO_HAS_DEFAULT_CAP_ON
        b.handState = MARIO_HAND_OPEN
        b.modelState = 0
        b.punchState = 0
        b.action = 0
        b.allowPartRotation = 0
        b.torsoAngle.x, b.torsoAngle.y, b.torsoAngle.z = 0, 0, 0
        b.headAngle.x, b.headAngle.y, b.headAngle.z = 0, 0, 0
    elseif gore_true(obj_has_behavior_id(o, id_bhvStaticObject)) then
        local index = (o.oBehParams >> 16) & MAX_PALETTES
        if index ~= 0 then
            look_borrow_palette(look_borrow(), index)
        end
    elseif sLive ~= nil and (gore_true(obj_has_behavior_id(o, id_bhvNormalCap))
    or (gore_true(obj_has_behavior_id(o, id_bhvMario)) and o.oBehParams == 1)) then
        look_restore()
    end
end)
if HOOK_ON_GEO_PROCESS ~= nil then
    hook_event(HOOK_ON_GEO_PROCESS, function(node)
        if sLive ~= nil and node ~= nil and node.type == GRAPH_NODE_TYPE_OBJECT then
            look_restore()
        end
    end)
end
hook_event(HOOK_ON_NAMETAGS_RENDER, function() look_restore() end)
hook_event(HOOK_ON_HUD_RENDER_BEHIND, function() look_restore() end)
hook_event(HOOK_ON_HUD_RENDER, function() look_restore() end)
hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    look_restore()
    if m.marioObj ~= nil and m.marioObj.hookRender == 0 then
        m.marioObj.hookRender = 1
    end
end)
hook_event(HOOK_UPDATE, function() look_restore() end)
end

local DEATH_WARP_WINDOW = 150
local WARP_ARRIVAL_WINDOW = 60
local REFILL_WINDOW     = 150

local sDeath = {
    pending = false,
    level = 0, area = 1, act = 0,
    last = 0,
    warpAt = nil,
    refill = false,
    refillAt = 0,
    messy = false,
}

local sDeathExitActions = {
    [ACT_DEATH_EXIT] = true,
    [ACT_UNUSED_DEATH_EXIT] = true,
    [ACT_FALLING_DEATH_EXIT] = true,
    [ACT_SPECIAL_DEATH_EXIT] = true,
}

hook_event(HOOK_ON_DEATH, function(m)
    if m.playerIndex ~= 0 then return end
    local np = gNetworkPlayers[0]
    local now = get_global_timer()

    if not sDeath.pending or now - sDeath.last > DEATH_WARP_WINDOW then
        sDeath.pending = true
        sDeath.level = np.currLevelNum
        sDeath.area = np.currAreaIndex
        sDeath.act = np.currActNum
        sDeath.warpAt = nil
    end
    sDeath.last = now

    if gOpt.death_blood and not sDeath.messy then
        sDeath.messy = true
        if (m.action & ACT_GROUP_MASK) ~= ACT_GROUP_SUBMERGED
        and m.floor ~= nil and m.floor.type ~= SURFACE_DEATH_PLANE and m.floor.type ~= SURFACE_BURNING
        and m.pos.y - m.floorHeight < 300 then
            squishblood_nogibs(m.marioObj)
        end
    end
end)

if HOOK_BEFORE_WARP ~= nil then
    hook_event(HOOK_BEFORE_WARP, function(destLevel, destArea, destWarpNode, arg)
        if sDeath.pending and arg ~= WARP_ARG_EXIT_COURSE and arg ~= 0xFFFFFFFF then
            sDeath.warpAt = get_global_timer()
        end
    end)
end

hook_event(HOOK_ON_WARP, function(warpType, levelNum, areaIdx, nodeId, warpArg)
    local m = gMarioStates[0]
    local s = gStateExtras[0]
    local np = gNetworkPlayers[0]
    local now = get_global_timer()

    request_restore()
    sDeath.messy = false

    if sDeath.refill then
        sDeath.refill = false
        if now - sDeath.refillAt <= REFILL_WINDOW then
            m.health = 0x880
            m.hurtCounter = 0
            m.healCounter = 0
            return
        end
    end

    if not sDeath.pending then return end
    sDeath.pending = false
    local warpAt = sDeath.warpAt
    sDeath.warpAt = nil

    if not gOpt.respawn_in_level then return end
    if now - sDeath.last > DEATH_WARP_WINDOW then return end
    if warpArg == WARP_ARG_EXIT_COURSE or warpArg == 0xFFFFFFFF then return end
    if s.iwbtg or gGlobalSyncTable.iwbtgmode or s.isinhell then return end
    if sDeath.level == LEVEL_HELL or sDeath.level == LEVEL_SECRETHUB then return end
    if (levelNum or np.currLevelNum) == sDeath.level then return end

    local costsLife = sDeathExitActions[m.action] == true

    local thrownOut = costsLife or (warpAt ~= nil and now - warpAt <= WARP_ARRIVAL_WINDOW)
    if not thrownOut then return end

    if not warp_to_level(sDeath.level, sDeath.area, sDeath.act) then
        if sDeath.area == 1 or not warp_to_level(sDeath.level, 1, sDeath.act) then
            return
        end
    end

    if costsLife then
        if not gOpt.infinite_lives then
            m.numLives = m.numLives - 1
        end
        m.health = 0x880
        m.hurtCounter = 0
        m.healCounter = 0
        sDeath.refill = true
        sDeath.refillAt = now
    end
end)

hook_event(HOOK_ON_LEVEL_INIT, function()
    request_restore()
    sDeath.pending = false
    sDeath.messy = false
end)

local sLivesFloor = nil

hook_event(HOOK_UPDATE, function()
    local m = gMarioStates[0]
    local s = gStateExtras[0]
    if gOpt.infinite_lives and not s.iwbtg and not gGlobalSyncTable.iwbtgmode and not s.isinhell and peach == nil then
        if sLivesFloor ~= nil and m.numLives < sLivesFloor then
            m.numLives = sLivesFloor
        end
        sLivesFloor = m.numLives
    else
        sLivesFloor = nil
    end
end)

local sMessyActions = {
    [ACT_GONE] = true,
    [ACT_RAGDOLL] = true,
    [ACT_NECKSNAP] = true,
    [ACT_DECAPITATED] = true,
    [ACT_BITTEN_IN_HALF] = true,
}

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    local s = gStateExtras[0]

    if s.enablesplattimer ~= 0 or s.splatterdeath ~= 0 or s.headless or s.bottomless or sMessyActions[m.action] then
        sDeath.messy = true
    end

    if not gOpt.onehit_all then return end
    if m.hurtCounter > 0 and m.health > 0xff and not s.isdead
    and not gore_fall_hurt()
    and s.splatter == 1 and s.splatterdeath == 0 and s.enablesplattimer == 0 and m.squishTimer == 0 then
        m.health = 0xff
        m.hurtCounter = 0
        sDeath.messy = true
        if m.floor ~= nil and m.floor.type ~= SURFACE_DEATH_PLANE and m.pos.y - m.floorHeight < 300 then
            squishblood(m.marioObj)
        else
            bloodmist(m.marioObj)
        end
        network_play(sSplatter, m.pos, 1, m.playerIndex)
    end
end)

local sKnock = {
    active = false,
    blood = false,
    touched = false,
    from = nil,
    smear = nil,
}

local function knock_reset()
    local smear = sKnock.smear
    sKnock.active = false
    sKnock.blood = false
    sKnock.touched = false
    sKnock.from = nil
    sKnock.smear = nil
    return smear
end

local sKnockBackward = {
    [ACT_SOFT_BACKWARD_GROUND_KB] = true,
    [ACT_BACKWARD_GROUND_KB] = true,
    [ACT_HARD_BACKWARD_GROUND_KB] = true,
    [ACT_BACKWARD_AIR_KB] = true,
    [ACT_HARD_BACKWARD_AIR_KB] = true,
}
local sKnockForward = {
    [ACT_SOFT_FORWARD_GROUND_KB] = true,
    [ACT_FORWARD_GROUND_KB] = true,
    [ACT_HARD_FORWARD_GROUND_KB] = true,
    [ACT_FORWARD_AIR_KB] = true,
    [ACT_HARD_FORWARD_AIR_KB] = true,
}
local sKnockHard = {
    [ACT_HARD_BACKWARD_GROUND_KB] = true,
    [ACT_HARD_FORWARD_GROUND_KB] = true,
    [ACT_HARD_BACKWARD_AIR_KB] = true,
    [ACT_HARD_FORWARD_AIR_KB] = true,
}
local sKnockWater = {
    [ACT_BACKWARD_WATER_KB] = true,
    [ACT_FORWARD_WATER_KB] = true,
}
local sDeathPoses = {
    [ACT_DEATH_ON_BACK] = true,
    [ACT_DEATH_ON_STOMACH] = true,
    [ACT_STANDING_DEATH] = true,
}

function gore_knockdown_active()
    return sKnock.active
end

function gore_ragdoll_landed(m)
    m.faceAngle.x = 0
    m.faceAngle.z = 0
    m.forwardVel = 0
    m.vel.x, m.vel.y, m.vel.z = 0, 0, 0
    if m.playerIndex == 0 then
        m.health = 0xff
        m.hurtCounter = 0
        sDeath.messy = true
        mario_blow_off_cap(m, 15)
        if m.marioObj ~= nil then
            m.marioObj.oPosX, m.marioObj.oPosY, m.marioObj.oPosZ = m.pos.x, m.pos.y, m.pos.z
            squishblood_nogibs(m.marioObj)
        end
        network_play(sSplatter, m.pos, 1, m.playerIndex)
        set_camera_shake_from_hit(SHAKE_LARGE_DAMAGE)
    end
    return set_mario_action(m, ACT_DEATH_ON_STOMACH, 0)
end

local function to_s16(angle)
    return ((math.floor(angle) + 0x8000) % 0x10000) - 0x8000
end

local function is_blast(o)
    return gore_true(obj_has_behavior_id(o, id_bhvExplosion))
        or gore_true(obj_has_behavior_id(o, id_bhvBowserBomb))
        or gore_true(obj_has_behavior_id(o, id_bhvBowserBombExplosion))
end

local BLAST_PUSH = 45

local SCRAPE_MIN     = 45
local SCRAPE_MAX     = 700
local SCRAPE_LENGTH  = 200
local SCRAPE_WIDTH   = 0.85
local SCRAPE_OVERLAP = 35
local WALL_SPLAT     = 0.6

local function to_angle(radians)
    return to_s16(radians / math.pi * 0x8000)
end

function gore_angles_on_surface(nx, ny, nz, yaw)
    local dx, dz = sins(yaw), coss(yaw)
    local dot = dx * nx + dz * nz
    local fx, fy, fz = dx - dot * nx, -dot * ny, dz - dot * nz
    local len = math.sqrt(fx * fx + fy * fy + fz * fz)
    if len < 0.001 or ny < 0.05 then
        return 0, to_s16(yaw), 0
    end
    fx, fy, fz = fx / len, fy / len, fz / len
    local pitch = math.asin(math.max(-1, math.min(1, -fy)))
    local cosPitch = math.cos(pitch)
    local roll = math.atan((nz * fx - nx * fz) / cosPitch, ny / cosPitch)
    return to_angle(pitch), to_angle(math.atan(fx, fz)), to_angle(roll)
end

local function knock_is_dying(m)
    return m.health <= 0xff or m.health - 0x40 * m.hurtCounter < 0x100
end

local function knock_can_bleed(m)
    return m.marioObj ~= nil and m.floor ~= nil and m.floor.type ~= SURFACE_DEATH_PLANE
        and m.floor.type ~= SURFACE_BURNING and m.pos.y - m.floorHeight < 300 and m.pos.y >= m.waterLevel
end

local function knock_wall_splat(m)
    local normal = m.wall.normal
    local yaw = atan2s(normal.z, normal.x)
    network_play(sSplatter, m.pos, 1, m.playerIndex)
    spawn_sync_object(id_bhvStaticObject, E_MODEL_BLOOD_SPLATTER,
        m.pos.x - 48 * sins(yaw), m.pos.y + 60, m.pos.z - 48 * coss(yaw),
        function(o)
            o.oFaceAnglePitch = 16384
            o.oFaceAngleYaw = yaw
            o.oFaceAngleRoll = 0
            obj_scale(o, WALL_SPLAT)
        end)
    if bloodmist ~= nil and m.marioObj ~= nil then bloodmist(m.marioObj) end
end

local function knock_scrape_place(x, z)
    local from = sKnock.from
    if from == nil then return nil end
    local dx, dz = x - from.x, z - from.z
    local dist = math.sqrt(dx * dx + dz * dz)
    if dist < SCRAPE_MIN then return nil end
    if dist > SCRAPE_MAX then
        dx, dz = dx / dist * SCRAPE_MAX, dz / dist * SCRAPE_MAX
        dist = SCRAPE_MAX
    end

    local midX, midZ = from.x + dx / 2, from.z + dz / 2
    local floor = collision_find_floor(midX, from.y + 150, midZ)
    if floor == nil or floor.type == SURFACE_DEATH_PLANE or floor.type == SURFACE_BURNING then return nil end
    local normal = floor.normal
    local pitch, yaw, roll = gore_angles_on_surface(normal.x, normal.y, normal.z, atan2s(dz, dx))
    return {
        x = midX, y = find_floor_height(midX, from.y + 150, midZ) + 3, z = midZ,
        pitch = pitch, yaw = yaw, roll = roll,
        length = (dist + 2 * SCRAPE_OVERLAP) / SCRAPE_LENGTH,
    }
end

local function knock_scrape_apply(o, place)
    o.oPosX, o.oPosY, o.oPosZ = place.x, place.y, place.z
    o.oFaceAnglePitch, o.oFaceAngleYaw, o.oFaceAngleRoll = place.pitch, place.yaw, place.roll
    o.oMoveAngleYaw = place.yaw
    obj_scale_xyz(o, SCRAPE_WIDTH, 1, place.length)
end

local function smear_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
    o.header.gfx.skipInViewCheck = true
end

local function smear_loop(o)
    if sKnock.smear == nil or o.oTimer > 300 then
        obj_mark_for_deletion(o)
    end
end

id_bhvGoreSmear = hook_behavior(nil, OBJ_LIST_UNIMPORTANT, true, smear_init, smear_loop, "bhvGoreSmear")

local function smear_alive(o)
    return o ~= nil and o.activeFlags ~= ACTIVE_FLAG_DEACTIVATED and gore_true(obj_has_behavior_id(o, id_bhvGoreSmear))
end

local function knock_scrape_update(m)
    local place = knock_scrape_place(m.pos.x, m.pos.z)
    if place == nil then return end
    local smear = sKnock.smear
    if smear_alive(smear) then
        knock_scrape_apply(smear, place)
    else
        sKnock.smear = spawn_non_sync_object(id_bhvGoreSmear, E_MODEL_BLOOD_SPLATTER2, place.x, place.y, place.z,
            function(o) knock_scrape_apply(o, place) end)
    end
end

local function knock_scrape_end(m)
    local smear = sKnock.smear
    sKnock.smear = nil
    if smear_alive(smear) then
        obj_mark_for_deletion(smear)
    end
    if sKnock.from == nil then return end
    local place = knock_scrape_place(m.pos.x, m.pos.z)
    sKnock.from = nil
    if place == nil then return end
    spawn_sync_object(id_bhvStaticObject, E_MODEL_BLOOD_SPLATTER2, place.x, place.y, place.z,
        function(o) knock_scrape_apply(o, place) end)
end

local function throw_cap_aside(m, travel)
    local yaw, vel = m.faceAngle.y, m.forwardVel
    local side = (math.random(2) == 1) and 0x4000 or -0x4000
    m.faceAngle.y = to_s16(travel + side - 0x400)
    m.forwardVel = 0
    mario_blow_off_cap(m, 18)
    m.faceAngle.y = yaw
    m.forwardVel = vel
end

local function knock_down(m, lethal)
    local back = sKnockBackward[m.action] == true
    local air = (m.action & ACT_FLAG_AIR) ~= 0
    local target
    if air then
        target = back and ACT_HARD_BACKWARD_AIR_KB or ACT_HARD_FORWARD_AIR_KB
    else
        target = back and ACT_HARD_BACKWARD_GROUND_KB or ACT_HARD_FORWARD_GROUND_KB
    end

    throw_cap_aside(m, back and (m.faceAngle.y + 0x8000) or m.faceAngle.y)

    if m.action ~= target then
        drop_and_set_mario_action(m, target, 1)
    end
    if not air and math.abs(m.forwardVel) < 24 then
        mario_set_forward_vel(m, back and -24 or 24)
    end

    if lethal then
        m.health = 0xff
        m.hurtCounter = 0
    end
    knock_scrape_end(m)
    sKnock.touched = false
    sKnock.active = true
    sKnock.blood = true

    set_camera_shake_from_hit(lethal and SHAKE_LARGE_DAMAGE or SHAKE_MED_DAMAGE)
    network_play(sPunch, m.pos, 1, m.playerIndex)
end

function gore_blast_fling(m, o, push)
    if m.playerIndex ~= 0 or o == nil or m.marioObj == nil or gore_fling == nil then return false end
    if m.action == ACT_RAGDOLL then return true end
    local action = m.action
    if sKnockWater[action] or (action & ACT_FLAG_SWIMMING) ~= 0 or m.pos.y < m.waterLevel - 100 then return false end

    local dx, dz = m.pos.x - o.oPosX, m.pos.z - o.oPosZ
    local away = (dx * dx + dz * dz > 1) and atan2s(dz, dx) or to_s16(m.faceAngle.y + 0x8000)

    local hadCap = (m.flags & MARIO_CAP_ON_HEAD) ~= 0
    if not gore_fling(m, o, push or BLAST_PUSH, true, away) then return false end

    m.hurtCounter = 0
    knock_scrape_end(m)
    knock_reset()
    if hadCap then throw_cap_aside(m, away) end
    set_camera_shake_from_hit(SHAKE_LARGE_DAMAGE)
    return true
end

local sReal = {}
do
local REAL_FLINCH, REAL_FLOOR, REAL_HEAD, REAL_HALF, REAL_RAM = 1, 2, 3, 4, 5

local REAL_RAM_SPEED = 15

local function real_fire_piranha(m, o)
    local scale = o.oFirePiranhaPlantNeutralScale
    if scale ~= nil and scale >= 1.5 then
        return { fate = REAL_HEAD, wedges = 4, blood = true }
    end
    return { fate = REAL_FLINCH, wedges = 1, blood = true }
end

local function real_bowser(m, o)
    local bowser = o.parentObj or o
    local forward, up = bowser.oForwardVel or 0, bowser.oVelY or 0
    local speed = math.sqrt(forward * forward + up * up)
    if speed >= REAL_RAM_SPEED then
        return { fate = REAL_RAM, wedges = 6, from = bowser, push = math.min(60, 25 + speed * 0.5) }
    end
    return { fate = REAL_FLOOR, wedges = 4, blood = true }
end

local sRealRules = {
    { id_bhvSwoop,             { fate = REAL_FLINCH, wedges = 1, blood = true } },
    { id_bhvMontyMole,         { fate = REAL_FLINCH, wedges = 1, blood = true } },
    { id_bhvSpiny,             { fate = REAL_FLINCH, wedges = 2, blood = true } },
    { id_bhvPokeyBodyPart,     { fate = REAL_FLINCH, wedges = 2, blood = true } },
    { id_bhvSnufit,            { fate = REAL_FLINCH, wedges = 1 } },
    { id_bhvMrIParticle,       { fate = REAL_FLINCH, wedges = 1 } },
    { id_bhvFirePiranhaPlant,  real_fire_piranha },
    { id_bhvSnufitBalls,       { fate = REAL_FLINCH, wedges = 3, blood = true } },
    { id_bhvMontyMoleRock,     { fate = REAL_FLOOR,  wedges = 2 } },
    { id_bhvKlepto,            { fate = REAL_FLOOR,  wedges = 2, blood = true, always = true } },
    { id_bhvJrbSlidingBox,     { fate = REAL_FLOOR,  wedges = 3 } },
    { id_bhvWigglerHead,       { fate = REAL_FLOOR,  wedges = 5 } },
    { id_bhvWigglerBody,       { fate = REAL_FLOOR,  wedges = 5 } },
    { id_bhvBowserBodyAnchor,  real_bowser },
    { id_bhvBub,               { wedges = 1, blood = true } },
    { id_bhvClamShell,         { wedges = 3, blood = true } },
    { id_bhvBubba,             { wedges = 2 } },
    { id_bhvSushiShark,        { fate = REAL_HALF, wedges = 6, blood = true } },
    { id_bhvUnagiSubobject,    { fate = REAL_HALF, wedges = 6, blood = true } },
}

local function real_rule(m, o)
    for _, entry in ipairs(sRealRules) do
        local id = entry[1]
        if id ~= nil and gore_true(obj_has_behavior_id(o, id)) then
            local rule = entry[2]
            if type(rule) == "function" then rule = rule(m, o) end
            return rule
        end
    end
    return nil
end

local function real_capless(m, wedges)
    if (m.flags & MARIO_CAP_ON_HEAD) == 0 then
        wedges = wedges + (wedges + 1) // 2
    end
    return wedges
end

local function real_damage(m, o, wedges)
    local was = 4 * real_capless(m, o.oDamageOrCoinValue or 0)
    m.hurtCounter = math.max(0, math.min(255, m.hurtCounter - was + 4 * real_capless(m, wedges)))
end

local function real_flinch(m)
    local action = m.action
    if (action & ACT_FLAG_AIR) ~= 0 then return end
    local back = sKnockBackward[action] == true
    local target = back and ACT_SOFT_BACKWARD_GROUND_KB or ACT_SOFT_FORWARD_GROUND_KB
    if action ~= target then
        set_mario_action(m, target, m.actionArg)
    end
    if math.abs(m.forwardVel) > 16 then
        mario_set_forward_vel(m, back and -16 or 16)
    end
end

local function real_decapitate(m)
    local s = gStateExtras[0]
    s.headless = true
    network_play(sSplatter, m.pos, 1, m.playerIndex)
    network_play(sCrunch, m.pos, 1, m.playerIndex)
    m.health = 0xff
    m.hurtCounter = 0
    set_camera_shake_from_hit(SHAKE_LARGE_DAMAGE)
    m.particleFlags = PARTICLE_MIST_CIRCLE
    drop_and_set_mario_action(m, ACT_DECAPITATED, 0)
end

local sCanStayUnder = HOOK_ALLOW_FORCE_WATER_ACTION ~= nil
if sCanStayUnder then
    hook_event(HOOK_ALLOW_FORCE_WATER_ACTION, function(m)
        if m.action == ACT_BITTEN_IN_HALF then return false end
    end)
end

local function real_bite_in_half(m, inWater)
    local s = gStateExtras[0]
    s.bottomless = true
    network_play(sSplatter, m.pos, 1, m.playerIndex)
    network_play(sCrunch, m.pos, 1, m.playerIndex)
    if inWater then
        bloodmist(m.marioObj)
    else
        squishblood(m.marioObj)
    end
    m.health = 0xff
    m.hurtCounter = 0
    mario_blow_off_cap(m, 15)
    set_camera_shake_from_hit(SHAKE_LARGE_DAMAGE)
    drop_and_set_mario_action(m, ACT_BITTEN_IN_HALF, 0)
end

local function real_hit(m, o, rule)
    local s = gStateExtras[0]
    local action = m.action
    local kills = gOpt.enemy_kills
    local inWater = sKnockWater[action] == true or (action & ACT_FLAG_SWIMMING) ~= 0
    local knockable = sKnockBackward[action] or sKnockForward[action]
    local fate = rule.fate

    if kills and fate == REAL_HALF and not s.bottomless and (sCanStayUnder or not inWater) then
        return real_bite_in_half(m, inWater)
    end
    if kills and fate == REAL_HEAD and not s.headless and not inWater then
        return real_decapitate(m)
    end

    if rule.wedges ~= nil then real_damage(m, o, rule.wedges) end
    local dying = gOpt.onehit_all or (kills and fate == REAL_HALF) or (m.health - 0x40 * m.hurtCounter <= 0xff)

    if rule.blood and bloodmist ~= nil and m.marioObj ~= nil then
        bloodmist(m.marioObj)
    end

    if inWater then
        if dying then
            m.health = 0xff
            m.hurtCounter = 0
        end
        return
    end

    if fate == REAL_RAM and kills then
        if gOpt.enemy_fling and gore_blast_fling(m, rule.from or o, rule.push) then return end
        dying = true
    end

    if not knockable then return end
    if dying then
        knock_down(m, true)
    elseif fate == REAL_FLINCH then
        real_flinch(m)
    else
        knock_down(m, false)
    end
end

local THROW_WEDGES   = 3
local TORNADO_WEDGES = 4
local THROW_MIN      = 30
local TORNADO_WAIT   = 3
local TORNADO_OUT    = 30

local sThrow = {
    wedges = 0,
    twirl = 0,
}

local sThrowLandings = {
    [ACT_FORWARD_GROUND_KB] = true,
    [ACT_BACKWARD_GROUND_KB] = true,
    [ACT_HARD_FORWARD_GROUND_KB] = true,
    [ACT_HARD_BACKWARD_GROUND_KB] = true,
    [ACT_HEAD_STUCK_IN_GROUND] = true,
    [ACT_BUTT_STUCK_IN_GROUND] = true,
    [ACT_FEET_STUCK_IN_GROUND] = true,
}

local function real_thrown_update(m)
    if m.playerIndex ~= 0 then return end
    local action = m.action
    local real = gOpt.enemy_real and (m.flags & MARIO_METAL_CAP) == 0

    if action == ACT_TWIRLING and m.prevAction == ACT_TORNADO_TWIRLING and real then
        sThrow.twirl = sThrow.twirl + 1
        if sThrow.twirl >= TORNADO_WAIT then
            sThrow.twirl = 0
            local tornado = m.usedObj
            if tornado ~= nil and m.marioObj ~= nil then
                m.faceAngle.y = obj_angle_to_object(m.marioObj, tornado)
            end
            if (m.flags & MARIO_CAP_ON_HEAD) ~= 0 then
                throw_cap_aside(m, m.faceAngle.y + 0x8000)
            end
            m.forwardVel = -TORNADO_OUT
            set_mario_action(m, ACT_THROWN_BACKWARD, 0)
            sThrow.wedges = TORNADO_WEDGES
        end
        return
    end
    sThrow.twirl = 0

    if action == ACT_THROWN_FORWARD or action == ACT_THROWN_BACKWARD then
        if m.prevAction == ACT_GRABBED and math.abs(m.forwardVel) >= THROW_MIN then
            sThrow.wedges = THROW_WEDGES
        end
        return
    end

    local wedges = sThrow.wedges
    if wedges == 0 then return end
    sThrow.wedges = 0
    if not real or not sThrowLandings[action] then return end

    local s = gStateExtras[0]
    if m.health <= 0xff or s.isdead or m.squishTimer ~= 0 or s.splatter ~= 1 or s.splatterdeath ~= 0
    or s.enablesplattimer ~= 0 or m.hurtCounter > 0 or gore_fall_hurt() then
        return
    end

    m.health = math.max(0xff, m.health - 0x100 * real_capless(m, wedges))
    if (m.flags & MARIO_CAP_ON_HEAD) ~= 0 then
        throw_cap_aside(m, sKnockBackward[action] and (m.faceAngle.y + 0x8000) or m.faceAngle.y)
    end
    knock_scrape_end(m)
    sKnock.touched = false
    sKnock.active = true
    sKnock.blood = true
    play_character_sound(m, CHAR_SOUND_ATTACKED)
    set_camera_shake_from_hit(SHAKE_MED_DAMAGE)
    network_play(sPunch, m.pos, 1, m.playerIndex)
end
hook_event(HOOK_MARIO_UPDATE, real_thrown_update)

hook_event(HOOK_ON_LEVEL_INIT, function()
    sThrow.wedges = 0
    sThrow.twirl = 0
end)

sReal.rule = real_rule
sReal.hit = real_hit
end

function gore_enemy_hit(m, o, intType, interacted)
    if m.playerIndex ~= 0 or not interacted or o == nil then return end
    if intType == INTERACT_PLAYER then return end
    if (o.oInteractStatus & INT_STATUS_ATTACKED_MARIO) == 0 then return end
    if (m.flags & MARIO_METAL_CAP) ~= 0 then return end

    local s = gStateExtras[0]
    if m.health <= 0xff or s.isdead or s.headless or s.bottomless or m.squishTimer ~= 0 or m.action == ACT_RAGDOLL
    or s.splatter ~= 1 or s.splatterdeath ~= 0 or s.enablesplattimer ~= 0 then
        return
    end

    local mode = gOpt.enemy_small
    local knocks = (mode == GORE_SMALL_KNOCK or mode == GORE_SMALL_KNOCK_DEAD)
    local hurt = m.hurtCounter > 0
    local action = m.action
    local knockable = sKnockBackward[action] or sKnockForward[action]

    if gOpt.enemy_real then
        local rule = sReal.rule(m, o)
        if rule ~= nil and (hurt or rule.always) then
            return sReal.hit(m, o, rule)
        end
    end

    local lethal = false
    if knocks and hurt then
        if gOpt.onehit_all then
            lethal = true
        elseif mode == GORE_SMALL_KNOCK_DEAD then
            lethal = gore_is_small_enemy(o) or (gOpt.enemy_kills and sKnockHard[action] == true)
        end
    end

    local blast = gOpt.explosion_death and hurt and is_blast(o)
    if blast then
        if gore_blast_fling(m, o) then return end
        lethal = true
    end

    if not lethal and hurt and gOpt.enemy_damage > 1 then
        local damage = o.oDamageOrCoinValue
        if (m.flags & MARIO_CAP_ON_HEAD) == 0 then
            damage = damage + (damage + 1) // 2
        end
        m.hurtCounter = math.min(255, m.hurtCounter + 4 * damage * (gOpt.enemy_damage - 1))
    end

    if not knocks and not blast then return end
    if knockable and knocks then
        knock_down(m, lethal)
    elseif lethal and (blast or sKnockWater[action] or (action & ACT_FLAG_SWIMMING) ~= 0) then
        m.health = 0xff
        m.hurtCounter = 0
    end
end

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or not sKnock.active then return end
    local action = m.action
    if sDeathPoses[action] then
        if sKnock.blood then
            sKnock.blood = false
            sDeath.messy = true
            knock_scrape_end(m)
            if not sKnock.touched and knock_can_bleed(m) then
                sKnock.touched = true
                squishblood_nogibs(m.marioObj)
            end
        end
    elseif sKnockBackward[action] or sKnockForward[action] then
        if sKnock.blood and knock_is_dying(m) then
            if (action & ACT_FLAG_AIR) ~= 0 then
                if not sKnock.touched and m.wall ~= nil then
                    sKnock.touched = true
                    sDeath.messy = true
                    knock_wall_splat(m)
                end
            elseif sKnock.from == nil then
                if knock_can_bleed(m) then
                    sKnock.from = { x = m.pos.x, y = m.floorHeight, z = m.pos.z }
                    sDeath.messy = true
                    if not sKnock.touched then
                        sKnock.touched = true
                        squishblood_nogibs(m.marioObj)
                    end
                end
            else
                knock_scrape_update(m)
            end
        end
    else
        knock_scrape_end(m)
        knock_reset()
    end
end)

hook_event(HOOK_ON_LEVEL_INIT, function()
    knock_reset()
end)

local WAVE_RADIUS      = 700
local WAVE_RADIUS_NUKE = 1700
local WAVE_HURT        = 0.5
local WAVE_AGAIN       = 15
local WAVE_FROM, WAVE_TO = 2, 5

local sWave = { x = 0, y = 0, z = 0, at = -1000 }

function gore_blast_wave(m, o, radius)
    if m.playerIndex ~= 0 or o == nil or m.marioObj == nil then return false end
    radius = radius or WAVE_RADIUS
    local action = m.action
    local s = gStateExtras[0]
    if m.health <= 0xff or m.squishTimer ~= 0 or m.invincTimer > 0 or action == ACT_RAGDOLL then return false end
    if s == nil or s.isdead or s.headless or s.bottomless or s.splatterdeath ~= 0 or s.enablesplattimer ~= 0 then return false end
    if (action & (ACT_FLAG_INTANGIBLE | ACT_FLAG_INVULNERABLE | ACT_FLAG_SWIMMING)) ~= 0 then return false end
    if sKnockBackward[action] or sKnockForward[action] or sKnockWater[action] then return false end
    if m.pos.y < m.waterLevel - 100 or (m.flags & MARIO_METAL_CAP) ~= 0 then return false end

    local dx, dy, dz = m.pos.x - o.oPosX, m.pos.y - o.oPosY, m.pos.z - o.oPosZ
    local dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist > radius then return false end
    local near = 1 - dist / radius

    local away = (dx * dx + dz * dz > 1) and atan2s(dz, dx) or to_s16(m.faceAngle.y + 0x8000)
    local back = math.abs(to_s16(away - m.faceAngle.y)) > 0x4000
    local air = (action & (ACT_FLAG_AIR | ACT_FLAG_ON_POLE | ACT_FLAG_HANGING)) ~= 0 or m.pos.y > m.floorHeight + 20
    local target
    if air then
        target = back and ACT_HARD_BACKWARD_AIR_KB or ACT_HARD_FORWARD_AIR_KB
    else
        target = back and ACT_HARD_BACKWARD_GROUND_KB or ACT_HARD_FORWARD_GROUND_KB
    end

    throw_cap_aside(m, away)
    m.faceAngle.y = back and to_s16(away + 0x8000) or away
    drop_and_set_mario_action(m, target, 1)
    local speed = 14 + 18 * near
    mario_set_forward_vel(m, back and -speed or speed)

    if near >= WAVE_HURT then
        m.hurtCounter = m.hurtCounter + 4
    end

    knock_scrape_end(m)
    sKnock.touched = false
    sKnock.active = true
    sKnock.blood = true

    set_camera_shake_from_hit(near >= WAVE_HURT and SHAKE_LARGE_DAMAGE or SHAKE_MED_DAMAGE)
    return true
end

local function wave_check(m, id)
    local o = obj_get_nearest_object_with_behavior_id(m.marioObj, id)
    if o == nil or o.oTimer < WAVE_FROM or o.oTimer > WAVE_TO then return end
    local now = get_global_timer()
    local dx, dy, dz = o.oPosX - sWave.x, o.oPosY - sWave.y, o.oPosZ - sWave.z
    if now - sWave.at < WAVE_AGAIN and now >= sWave.at and dx * dx + dy * dy + dz * dz < 100 then return end
    sWave.x, sWave.y, sWave.z, sWave.at = o.oPosX, o.oPosY, o.oPosZ, now
    local nuke = gOpt.nukes and id == id_bhvExplosion and o.oBehParams ~= 20
    gore_blast_wave(m, o, nuke and WAVE_RADIUS_NUKE or WAVE_RADIUS)
end

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or not gOpt.blast_wave or m.marioObj == nil then return end
    wave_check(m, id_bhvExplosion)
    wave_check(m, id_bhvBowserBombExplosion)
end)

local WOUND_TICK = 0x20
local FRESH_LIFE_FRAMES = 60

local sWound = {
    ceil = nil,
    last = nil,
    grace = 0,
}

local sFreshLifeActions = {
    [ACT_EXIT_AIRBORNE] = true,
    [ACT_FALLING_EXIT_AIRBORNE] = true,
    [ACT_SPECIAL_EXIT_AIRBORNE] = true,
    [ACT_EXIT_LAND_SAVE_DIALOG] = true,
    [ACT_DEATH_EXIT] = true,
    [ACT_UNUSED_DEATH_EXIT] = true,
    [ACT_FALLING_DEATH_EXIT] = true,
    [ACT_SPECIAL_DEATH_EXIT] = true,
    [ACT_DEATH_EXIT_LAND] = true,
}

local function wounds_apply()
    local s = gStateExtras[0]
    return gOpt.no_healing and not s.iwbtg and not gGlobalSyncTable.iwbtgmode and not s.isinhell and peach == nil
end

hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 or sWound.ceil == nil or sWound.grace > 0 then return end
    if wounds_apply() then
        m.healCounter = 0
    end
end)

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    if not wounds_apply() then
        sWound.ceil = nil
        sWound.last = nil
        sWound.grace = 0
        return
    end

    local health = m.health
    if health < 0x100 or sFreshLifeActions[m.action] then
        sWound.grace = FRESH_LIFE_FRAMES
    end

    if sWound.grace > 0 or sWound.ceil == nil then
        if sWound.grace > 0 then sWound.grace = sWound.grace - 1 end
        sWound.ceil = math.max(health, 0x100)
    else
        local lost = (sWound.last or health) - health
        if health > sWound.ceil then
            health = sWound.ceil
            m.health = health
        elseif lost >= WOUND_TICK then
            sWound.ceil = math.max(health, sWound.ceil - lost)
        end
        m.healCounter = 0
    end
    sWound.last = health
end)

local FULL_WEDGES = 8

local function wedges_lost(m)
    if m.health < 0x100 then return 0 end
    local s = gStateExtras[m.playerIndex]
    if s == nil or s.iwbtg or gGlobalSyncTable.iwbtgmode or s.isinhell or peach ~= nil then return 0 end
    if (m.flags & MARIO_METAL_CAP) ~= 0 then return 0 end
    return math.max(0, FULL_WEDGES - (m.health >> 8))
end

local LIMP_RUN, LIMP_JUMP = 0.07, 0.02
local MAX_RUN_SPEED = 32

local sLimpRun = {
    [ACT_WALKING] = true,
    [ACT_HOLD_WALKING] = true,
}
local sLimpJump = {
    [ACT_JUMP] = true,
    [ACT_HOLD_JUMP] = true,
    [ACT_DOUBLE_JUMP] = true,
    [ACT_TRIPLE_JUMP] = true,
    [ACT_BACKFLIP] = true,
    [ACT_SIDE_FLIP] = true,
    [ACT_LONG_JUMP] = true,
    [ACT_WALL_KICK_AIR] = true,
    [ACT_STEEP_JUMP] = true,
}

hook_event(HOOK_BEFORE_PHYS_STEP, function(m)
    if not gOpt.wound_limp or not sLimpRun[m.action] then return end
    local lost = wedges_lost(m)
    if lost <= 1 then return end
    local max = MAX_RUN_SPEED * (1 - LIMP_RUN * (lost - 1))
    if m.forwardVel > max then
        local k = max / m.forwardVel
        m.vel.x = m.vel.x * k
        m.vel.z = m.vel.z * k
        m.forwardVel = max
    end
end)

hook_event(HOOK_ON_SET_MARIO_ACTION, function(m)
    if not gOpt.wound_limp or not sLimpJump[m.action] or m.vel.y <= 0 then return end
    local lost = wedges_lost(m)
    if lost <= 1 then return end
    m.vel.y = m.vel.y * (1 - LIMP_JUMP * (lost - 1))
end)

local DRIP_LIFE = 900
local DRIP_FADE = 30
local DRIP_MAX = 150
local DRIP_MIN_DIST = 35

local function drip_init(o)
    o.oFlags = OBJ_FLAG_UPDATE_GFX_POS_AND_ANGLE
    local floor = cur_obj_update_floor_height_and_get_floor()
    if floor ~= nil then
        local z, normal = vec3f(), floor.normal
        o.oFaceAnglePitch = 16384 - calculate_pitch(z, normal)
        o.oFaceAngleYaw = calculate_yaw(z, normal)
        o.oFaceAngleRoll = 0
    end
end

local function drip_loop(o)
    local left = DRIP_LIFE - o.oTimer
    if left <= 0 then
        obj_mark_for_deletion(o)
    elseif left < DRIP_FADE then
        obj_scale(o, (o.oBehParams / 100) * (left / DRIP_FADE))
    end
end

id_bhvGoreDrip = hook_behavior(nil, OBJ_LIST_UNIMPORTANT, true, drip_init, drip_loop, "bhvGoreDrip")

local sDrip = {}

hook_event(HOOK_MARIO_UPDATE, function(m)
    if not gOpt.wound_bleed then return end
    local i = m.playerIndex
    if i ~= 0 and not gore_true(is_player_active(m)) then return end

    local lost = wedges_lost(m)
    if lost < 2 then
        sDrip[i] = nil
        return
    end
    local d = sDrip[i]
    if d == nil then
        d = { wait = 0, x = nil, z = nil }
        sDrip[i] = d
    end
    if d.wait > 0 then
        d.wait = d.wait - 1
        return
    end

    local floor = m.floor
    if m.marioObj == nil or floor == nil or floor.type == SURFACE_DEATH_PLANE or floor.type == SURFACE_BURNING
    or m.pos.y - m.floorHeight > 120 or m.pos.y < m.waterLevel
    or (m.action & (ACT_FLAG_SWIMMING | ACT_FLAG_INTANGIBLE)) ~= 0 then
        return
    end
    if d.x ~= nil then
        local dx, dz = m.pos.x - d.x, m.pos.z - d.z
        if dx * dx + dz * dz < DRIP_MIN_DIST * DRIP_MIN_DIST then return end
    end
    if obj_count_objects_with_behavior_id(id_bhvGoreDrip) >= DRIP_MAX then
        d.wait = 30
        return
    end

    local size = math.random(10, 16) + lost * 2
    spawn_non_sync_object(id_bhvGoreDrip, E_MODEL_BLOOD_SPLATTER,
        m.pos.x + math.random(-12, 12), m.floorHeight + 1.5 + math.random() * 1.5, m.pos.z + math.random(-12, 12),
        function(o)
            o.oBehParams = size
            o.oOpacity = 255
            obj_scale(o, size / 100)
        end)
    d.x, d.z = m.pos.x, m.pos.z
    d.wait = (lost >= 6 and 10) or (lost >= 4 and 20) or 38
end)

hook_event(HOOK_ON_LEVEL_INIT, function()
    sDrip = {}
end)

local TEX_WOUND = get_texture_info("bloodoverlay")

local sVisionAlpha = { [0] = 0, 0, 0, 22, 42, 62, 86, 112, 135 }
local VISION_DEAD = 135
local VISION_FLASH = 95
local VISION_STEP = 3

local sVision = { alpha = 0, flash = 0, beat = 0, health = nil, at = nil }

local function vision_alpha()
    local m = gMarioStates[0]
    local now = get_global_timer()
    local frames = (sVision.at == nil) and 1 or (now - sVision.at)
    if frames < 0 or frames > 30 then frames = 1 end
    sVision.at = now

    local target, lost = 0, 0
    if gOpt.wound_vision and m ~= nil and m.marioObj ~= nil then
        lost = wedges_lost(m)
        target = sVisionAlpha[lost] or 0
        local s = gStateExtras[0]
        if m.health < 0x100 and s ~= nil and not s.iwbtg and not s.isinhell and peach == nil then
            target = VISION_DEAD
        end
        if sVision.health ~= nil and frames > 0 and m.health < sVision.health - 0x80 * frames and target > 0 then
            sVision.flash = VISION_FLASH
        end
        sVision.health = m.health
    else
        sVision.health = nil
        sVision.flash = 0
    end

    if frames > 0 then
        local step = VISION_STEP * frames
        if sVision.alpha < target then
            sVision.alpha = math.min(target, sVision.alpha + step)
        else
            sVision.alpha = math.max(target, sVision.alpha - step)
        end
        sVision.flash = math.max(0, sVision.flash - 5 * frames)
        local period = 40 - 5.5 * math.max(0, lost - 3)
        sVision.beat = (sVision.beat + frames / period) % 1
    end

    if sVision.alpha <= 0 and sVision.flash <= 0 then return 0 end
    local t = sVision.beat
    local thump = math.max(0, 1 - t / 0.16) + 0.6 * math.max(0, 1 - math.abs(t - 0.3) / 0.14)
    local a = sVision.alpha * (0.8 + 0.35 * math.min(1, thump)) + sVision.flash
    return math.floor(math.max(0, math.min(255, a)))
end

hook_event(HOOK_ON_HUD_RENDER, function()
    local alpha = vision_alpha()
    if alpha <= 0 or TEX_WOUND == nil then return end
    djui_hud_set_resolution(RESOLUTION_DJUI)
    djui_hud_set_color(255, 255, 255, alpha)
    djui_hud_render_texture(TEX_WOUND, 0, 0, djui_hud_get_screen_width() / 512, djui_hud_get_screen_height() / 512)
    djui_hud_set_color(255, 255, 255, 255)
end)

hook_event(HOOK_ON_LEVEL_INIT, function()
    sVision.health = nil
end)

local sBleeders = {
    [id_bhvGoomba]          = 0.30,
    [id_bhvKoopa]           = 0.35,
    [id_bhvScuttlebug]      = 0.40,
    [id_bhvSwoop]           = 0.25,
    [id_bhvFlyGuy]          = 0.35,
    [id_bhvSkeeter]         = 0.40,
    [id_bhvSnufit]          = 0.30,
    [id_bhvMontyMole]       = 0.30,
    [id_bhvEnemyLakitu]     = 0.40,
    [id_bhvSpindrift]       = 0.35,
    [id_bhvSpiny]           = 0.25,
    [id_bhvPokeyBodyPart]   = 0.25,
    [id_bhvPiranhaPlant]    = 0.50,
    [id_bhvFirePiranhaPlant] = 0.35,
    [id_bhvMoneybag]        = 0.30,
}
local BLEED_MAX_DROP = 500
local BLEED_AGAIN = 20

local sBled = {}

local function bleeder_size(o)
    for id, size in pairs(sBleeders) do
        if gore_true(obj_has_behavior_id(o, id)) then
            if id == id_bhvGoomba then
                if gore_true(obj_has_model_extended(o, E_MODEL_WOODEN_SIGNPOST)) then return nil end
                local scale = o.header.gfx.scale.x
                if scale ~= nil and scale > 0 then
                    size = math.max(0.12, math.min(0.8, size * scale / 1.5))
                end
            elseif id == id_bhvKoopa and o.oKoopaMovementType ~= KOOPA_BP_UNSHELLED then
                return nil
            end
            return size
        end
    end
    return nil
end

hook_event(HOOK_ON_INTERACT, function(m, o, intType, interacted)
    if not gOpt.enemy_bleed or m.playerIndex ~= 0 or not interacted or o == nil then return end
    if (o.oInteractStatus & INT_STATUS_WAS_ATTACKED) == 0 then return end
    local size = bleeder_size(o)
    if size == nil then return end

    local now = get_global_timer()
    local x, y, z = o.oPosX, o.oPosY, o.oPosZ
    local kept = {}
    for _, b in ipairs(sBled) do
        if now - b.at < BLEED_AGAIN and now >= b.at then
            local dx, dz = x - b.x, z - b.z
            if dx * dx + dz * dz < 150 * 150 then return end
            kept[#kept + 1] = b
        end
    end
    kept[#kept + 1] = { x = x, z = z, at = now }
    sBled = kept

    if bloodmist ~= nil then bloodmist(o) end

    local floorY = find_floor_height(x, y + 60, z)
    if floorY == nil or floorY < -10000 or y - floorY > BLEED_MAX_DROP then return end
    local floor = collision_find_floor(x, y + 60, z)
    if floor == nil or floor.type == SURFACE_DEATH_PLANE or floor.type == SURFACE_BURNING then return end
    local water = find_water_level(x, z)
    if water ~= nil and water > floorY then return end

    spawn_sync_object(id_bhvSquishblood, E_MODEL_BLOOD_SPLATTER, x, floorY + 2, z, function(b)
        b.oBehParams = 1
        obj_scale(b, size)
    end)
end)

hook_event(HOOK_ON_LEVEL_INIT, function()
    sBled = {}
end)

local HIT_COOLDOWN = 30
local HIT_GUARD    = 3
local HIT_APART    = 3

local sHit = {
    real = nil,
    bare = nil,
    open = false,
    grace = false,
    sets = 0,
    seen = 0,
    by = {},
    before = nil,
    last = nil,
    down = {},
    can = HOOK_ALLOW_INTERACT ~= nil and HOOK_BEFORE_SET_MARIO_ACTION ~= nil and HOOK_ON_INTERACTIONS ~= nil
        and HOOK_ALLOW_PVP_ATTACK ~= nil,
}
for _, actions in ipairs({ sKnockBackward, sKnockForward, sKnockWater }) do
    for action in pairs(actions) do sHit.down[action] = true end
end

local function hit_restore(m)
    local real, bare = sHit.real, sHit.bare
    if real == nil then return end
    sHit.real, sHit.bare = nil, nil
    if m.action == bare then m.action = real end
    if m.prevAction == bare then m.prevAction = real end
end

local function hit_same(a, b)
    if a == b then return true end
    return type(a) == "table" and type(b) == "table" and a._pointer ~= nil and a._pointer == b._pointer
end

local function hit_floor_plain(m)
    local floor = m.floor
    if floor == nil then return false end
    local t = floor.type
    return t ~= SURFACE_DEATH_PLANE and t ~= SURFACE_VERTICAL_WIND and t ~= SURFACE_WARP and t ~= SURFACE_BURNING
end

local sHitFlat = {
    [ACT_HARD_BACKWARD_GROUND_KB] = { at = 43, death = ACT_DEATH_ON_BACK },
    [ACT_HARD_FORWARD_GROUND_KB]  = { at = 23, death = ACT_DEATH_ON_STOMACH },
}
local HIT_FLAT_BEFORE = 3

local function hit_anim_frame(m, frame)
    local o = m.marioObj
    if o == nil then return end
    set_anim_to_frame(m, frame)
    o.header.gfx.animInfo.animFrame = frame - 1
end

local function hit_while_down(m, before)
    local flat = sHitFlat[before]
    local action = m.action
    if flat == nil then
        hit_anim_frame(m, 0)
        return
    end
    if action ~= before then
        if (action & (ACT_FLAG_AIR | ACT_FLAG_SWIMMING)) ~= 0 then return end
        if gOpt.enemy_kills and not sKnock.active then
            hit_anim_frame(m, 0)
            return
        end
        set_mario_action(m, before, m.actionArg)
        if m.action ~= before then return end
    end
    local o = m.marioObj
    if o ~= nil and o.header.gfx.animInfo.animFrame > flat.at - HIT_FLAT_BEFORE then
        hit_anim_frame(m, flat.at - HIT_FLAT_BEFORE)
    end
end

local function hit_hook(event, f)
    if event ~= nil then hook_event(event, f) end
end

local function hit_only_down(m)
    local s = gStateExtras[0]
    return m.squishTimer == 0 and s ~= nil and not s.isdead and not s.headless
        and not s.bottomless and s.splatter == 1 and s.splatterdeath == 0 and s.enablesplattimer == 0
end

function gore_hit_open()
    return sHit.open
end

hook_event(HOOK_BEFORE_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    hit_restore(m)
    sHit.open = false

    local action = m.action
    if sHit.can and gOpt.hit_cooldown == GORE_COOLDOWN_NONE and sHit.down[action]
    and (action & ACT_FLAG_INVULNERABLE) ~= 0 and m.invincTimer == 0 and hit_floor_plain(m) then
        if not knock_is_dying(m) and hit_only_down(m) then
            sHit.open = true
        end
    end

    if not sHit.down[action] and sHit.by[1] ~= nil then sHit.by = {} end
    if not sHit.open then return end
    sHit.real = action
    sHit.bare = action & ~ACT_FLAG_INVULNERABLE
    m.action = sHit.bare
end)

hit_hook(HOOK_BEFORE_SET_MARIO_ACTION, function(m, action)
    if m.playerIndex ~= 0 then return end
    hit_restore(m)
    sHit.sets = sHit.sets + 1
    if sHit.down[action] and not sHit.down[m.action] and gOpt.hit_cooldown ~= GORE_COOLDOWN_NORMAL then
        hit_anim_frame(m, 0)
    end
end)

hit_hook(HOOK_ALLOW_INTERACT, function(m, o, intType)
    if m.playerIndex ~= 0 then return end
    hit_restore(m)
    sHit.seen = sHit.sets
    sHit.before = m.action
    if o == nil or intType == INTERACT_PLAYER then return end

    local now = get_global_timer()
    for i, hit in ipairs(sHit.by) do
        if hit_same(hit.o, o) then
            local apart = now - hit.at
            if apart < 0 or apart > HIT_APART then
                table.remove(sHit.by, i)
                return
            end
            hit.at = now
            if sHit.open then return false end
            return
        end
    end
end)

hook_event(HOOK_ON_INTERACT, function(m, o, intType, interacted)
    if m.playerIndex ~= 0 or not interacted or o == nil or intType == INTERACT_PLAYER then return end
    if gOpt.hit_cooldown == GORE_COOLDOWN_NORMAL then return end
    if sHit.sets == sHit.seen or not sHit.down[m.action] then return end
    if sHit.down[sHit.before] then hit_while_down(m, sHit.before) end
    if gOpt.hit_cooldown ~= GORE_COOLDOWN_NONE or not sHit.down[m.action] then return end

    local now = get_global_timer()
    for _, hit in ipairs(sHit.by) do
        if hit_same(hit.o, o) then
            hit.at = now
            return
        end
    end
    sHit.by[#sHit.by + 1] = { o = o, at = now }
end)

hit_hook(HOOK_ALLOW_PVP_ATTACK, function(attacker)
    if attacker.playerIndex ~= 0 then return end
    local bare = sHit.real ~= nil
    hit_restore(attacker)
    if bare then return false end
end)

hit_hook(HOOK_ON_INTERACTIONS, function(m)
    if m.playerIndex ~= 0 then return end
    hit_restore(m)
end)

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    hit_restore(m)

    local timer = m.invincTimer
    if timer > HIT_COOLDOWN then
        sHit.grace = true
    elseif timer <= 0 then
        sHit.grace = false
    elseif timer > HIT_GUARD and not sHit.grace and gOpt.hit_cooldown ~= GORE_COOLDOWN_NORMAL then
        m.invincTimer = 0
    end

    local action = m.action
    local flat = sHitFlat[action]
    if flat ~= nil and sHit.last == action and m.health < 0x100 and gOpt.hit_cooldown ~= GORE_COOLDOWN_NORMAL
    and m.marioObj ~= nil and m.marioObj.header.gfx.animInfo.animFrame > flat.at and hit_only_down(m) then
        set_mario_action(m, flat.death, 0)
    end
    sHit.last = m.action
end)

hook_event(HOOK_ON_LEVEL_INIT, function()
    sHit.by = {}
    sHit.open = false
end)
