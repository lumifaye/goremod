-- Whose save a game uses ("The host's stores" in persist.lua), tried without the game.
-- Three games (a host and two guests) run persist.lua side by side; the game's functions and the network
-- between them are faked. Run it from the top of the repository with any Lua 5.3 or 5.4:
--     lua fork/tests/persist_net_test.lua
local SRC = "persist.lua"
local wire = {}
local games = {}
local timer = 100

local function copy(t) local c = {} for k, v in pairs(t) do c[k] = v end return c end

local function make_game(name, isServer, myGlobal, peers)
    local G = { name = name, hooks = {}, storage = {}, chat = {} }
    local consts = 0
    local env = {}
    env.MAX_PLAYERS = 16
    env.PLAYER_PART_MAX = 8
    env.gOpt = { blood_save = true, blood_unlimited = true, blood_max = 40, blood_forever = true, cap_forever = true, body_forever = true }
    env.gNetworkPlayers = {}
    env.gMarioStates = {}
    for i = 0, 15 do
        env.gNetworkPlayers[i] = { connected = false, globalIndex = 0, localIndex = i, currLevelNum = 9, currAreaIndex = 1, currAreaSyncValid = true }
        env.gMarioStates[i] = { playerIndex = i, active = false, pos = { x = 0, y = 0, z = 0 } }
    end
    for li, gi in pairs(peers) do
        env.gNetworkPlayers[li].connected = true
        env.gNetworkPlayers[li].globalIndex = gi
        env.gMarioStates[li].active = true
    end
    env.gNetworkPlayers[0].connected = true
    env.gNetworkPlayers[0].globalIndex = myGlobal
    G.peers = peers
    env.network_is_server = function() return isServer end
    env.network_local_index_from_global = function(g)
        for li = 0, 15 do
            local np = env.gNetworkPlayers[li]
            if np.connected and np.globalIndex == g then return li end
        end
        return 0
    end
    env.network_global_index_from_local = function(l) return env.gNetworkPlayers[l].globalIndex end
    env.is_player_active = function(m) return m.active and 1 or 0 end
    env.gore_true = function(v) return v ~= nil and v ~= false and v ~= 0 end
    env.get_global_timer = function() return timer end
    env.hook_event = function(e, f) if e ~= nil then G.hooks[e] = G.hooks[e] or {}; table.insert(G.hooks[e], f) end end
    env.hook_behavior = function() consts = consts + 1; return 5000 + consts end
    env.djui_chat_message_create = function(s) G.chat[#G.chat + 1] = s end
    env.mod_storage_load = function(k) return G.storage[k] end
    env.mod_storage_save = function(k, v) G.storage[k] = v; G.saves = (G.saves or 0) + 1; return true end
    env.mod_storage_remove = function(k) G.storage[k] = nil; return true end
    env.mod_storage_load_all = function() return copy(G.storage) end
    env.obj_get_first_with_behavior_id = function() return nil end
    env.obj_count_objects_with_behavior_id = function() return 0 end
    env.network_send_to = function(li, reliable, t)
        local gi = env.gNetworkPlayers[li].globalIndex
        assert(li > 0 and env.gNetworkPlayers[li].connected, name .. ": send to nobody")
        for k, v in pairs(t) do
            if type(v) == "string" then assert(#v >= 1 and #v <= 256, "string of " .. #v) end
            assert(type(v) == "string" or type(v) == "number" or type(v) == "boolean", "value type " .. type(v))
        end
        local size = 0
        for k, v in pairs(t) do size = size + 12 + (type(v) == "string" and #v + 3 or 9) end
        assert(size < 2900, "packet of " .. size)
        G.sent = (G.sent or 0) + 1
        wire[#wire + 1] = { to = games[gi], data = copy(t) }
    end
    env.network_send = function(reliable, t)
        for li, gi in pairs(peers) do wire[#wire + 1] = { to = games[gi], data = copy(t) } end
    end
    env._G = env
    setmetatable(env, { __index = function(_, k)
        local v = _G[k]
        if v ~= nil then return v end
        if type(k) == "string" and (k:match("^[A-Z_0-9]+$") or k:match("^id_") or k:match("^E_MODEL")) then
            if k:match("^HOOK_") then rawset(env, k, k) return k end
            if k == "MOD_FS_MAX_SIZE" or k == "MOD_FS_MAX_FILES" or k == "OBJECT_POOL_CAPACITY" or k == "FILE_SEEK_END" then return nil end
            consts = consts + 1
            rawset(env, k, 1000 + consts)
            return 1000 + consts
        end
        if type(k) == "string" and k:match("^g[A-Z]") then local tb = {}; rawset(env, k, tb); return tb end
        if type(k) == "string" and k:match("^[a-z_0-9]+$") and not k:match("^mod_fs_") and k ~= "obj_get_first" and k ~= "obj_get_next" then
            return function() return nil end
        end
        return nil
    end })
    local chunk = assert(loadfile(SRC, "t", env))
    chunk()
    G.env = env
    G.fire = function(e, ...) for _, f in ipairs(G.hooks[e] or {}) do f(...) end end
    local seen, found = {}, {}
    local function walk(f, depth)
        if seen[f] or depth > 6 then return end
        seen[f] = true
        local i = 1
        while true do
            local n, v = debug.getupvalue(f, i)
            if n == nil then break end
            if n ~= "_ENV" then
                if found[n] == nil then found[n] = v end
                if type(v) == "function" then walk(v, depth + 1) end
                if type(v) == "table" and n == "sNet" then for _, g in pairs(v) do if type(g) == "function" then walk(g, depth + 1) end end end
            end
            i = i + 1
        end
    end
    for _, list in pairs(G.hooks) do for _, f in ipairs(list) do walk(f, 0) end end
    walk(env.gore_persist_wipe, 0)
    G.f = found
    games[myGlobal] = G
    return G
end

local function deliver()
    local n = 0
    while #wire > 0 do
        local p = table.remove(wire, 1)
        n = n + 1
        p.to.fire("HOOK_ON_PACKET_RECEIVE", p.data)
    end
    return n
end
local function frames(count)
    for _ = 1, count do
        timer = timer + 1
        for _, g in pairs(games) do
            for _, f in ipairs(g.hooks["HOOK_UPDATE"] or {}) do
                local n, v = debug.getupvalue(f, 1)
                local info = debug.getinfo(f, "S")
                if g.netUpdate == nil then
                    local i = 1
                    while true do
                        local un = debug.getupvalue(f, i)
                        if un == nil then break end
                        if un == "tell_update" or un == "send_update" then g.netUpdate = f end
                        i = i + 1
                    end
                end
            end
            if g.netUpdate then g.netUpdate() end
        end
        deliver()
    end
end
local function ok(c, msg) if not c then error("FAIL " .. msg, 2) end print("ok  " .. msg) end
local function count(st, lo, hi) local n = 0 for _, e in ipairs(st.list) do if e.m >= lo and e.m <= hi then n = n + 1 end end return n end

local host = make_game("host", true, 0, { [1] = 1, [2] = 2 })
local A = make_game("A", false, 1, { [1] = 0, [2] = 2 })
local B = make_game("B", false, 2, { [1] = 0, [2] = 1 })
for _, n in ipairs({ "store_get", "records_read", "store_add", "sStores", "sNet", "sScan", "flush_stores", "record_of" }) do
    ok(host.f[n] ~= nil, "found " .. n)
end

local pal = "1,2,3,4,5,6,7,8"
local pal2 = "9,9,9,9,9,9,9,9"
local hs = host.f.store_get("9_1")
local raw = {}
raw[#raw + 1] = "10,100,0,100,0,0,0,100,5,3,100,0,189," .. pal
raw[#raw + 1] = "10,2000,0,100,0,0,0,100,5,3,100,1,189," .. pal2 .. ",123456,2"
raw[#raw + 1] = "15,4000,0,100,0,0,0,100,5,3,100,0,189"
raw[#raw + 1] = "5,300,0,300,0,0,0,100," .. pal
raw[#raw + 1] = "6,600,0,300,0,0,0,100"
for i = 1, 3000 do raw[#raw + 1] = "1," .. (i * 40) .. ",0," .. (-i * 40) .. ",0," .. i .. ",0,100" .. (i % 7 == 0 and ",250" or "") end
host.f.records_read(table.concat(raw, ";"), hs)
ok(#hs.list == 3005, "host has 3005 entries")

A.storage["B9_1_n"] = "1"
A.storage["B9_1_1"] = "1,7777,0,7777,0,0,0,100;10,7000,0,7000,0,0,0,100,5,3,100,0,189"
local as = A.f.store_get("9_1")
ok(#as.list == 0, "the guest's own save is not read")
ok(#B.f.store_get("9_1").list == 0, "nor guest B's")

A.f.sNet.ask("9_1")
ok(#wire == 1 and wire[1].to == host, "one question to the host")
A.f.sNet.ask("9_1")
ok(#wire == 1, "not asked twice in a row")
deliver()
frames(1)
ok(count(as, 10, 24) == 3 and count(as, 5, 9) == 2, "bodies and caps arrive first (" .. #as.list .. " entries after one frame)")
frames(400)
ok(#as.list == 3005, "everything arrived: " .. #as.list)
ok(as.hostSerial == host.f.sNet.serial, "the guest knows how far he is")
local hb, ab
for _, e in ipairs(hs.list) do if e.g == 123456 then hb = e end end
for _, e in ipairs(as.list) do if e.g == 123456 then ab = e end end
ok(ab ~= nil and ab.j == 2 and ab.k == pal2 and ab.c == 1 and ab.x == 2000, "the character, costume, colours and cap flag of a body came across")
local same = true
for i = 1, 3000 do if host.f.record_of(hs.list[5 + i]) ~= A.f.record_of(as.list[5 + i]) then same = false end end
ok(same, "the stains are the same, in the same order")
local sentBefore = host.sent
A.f.sNet.ask("9_1")
timer = timer + 200
A.f.sNet.ask("9_1"); deliver(); frames(5)
ok(host.sent == sentBefore + 1 and #as.list == 3005, "asking again brings one empty packet, nothing twice")

A.saves = 0
as.dirty = true; as.dirtyAt = 0
A.f.flush_stores()
ok(A.saves == 0 and A.storage["B9_1_1"] == "1,7777,0,7777,0,0,0,100;10,7000,0,7000,0,0,0,100,5,3,100,0,189", "the guest's save is not written")

local function body(x, z, k) return { m = 10, x = x, y = 0, z = z, p = 0, w = 0, r = 0, s = 100, a = 5, f = 3, v = 100, c = 0, t = 189, k = k } end
host.f.store_add(hs, body(9000, 9000, pal))
A.f.store_add(as, body(9040, 8990, pal))
ok(#wire == 0, "the host was there: the guest tells him nothing")
timer = timer + 200
A.f.sNet.ask("9_1"); deliver(); frames(5)
ok(count(as, 10, 24) == 4, "the host's copy of a body the guest noted himself is left out")
host.f.store_add(hs, body(9100, 9000, pal))
timer = timer + 200
A.f.sNet.ask("9_1"); deliver(); frames(5)
ok(count(as, 10, 24) == 5, "a second body at the same spot does arrive")

A.env.gMarioStates[1].active = false
B.env.gMarioStates[1].active = false
local a2, b2 = A.f.store_get("5_1"), B.f.store_get("5_1")
A.f.store_add(a2, body(500, 500, pal))
B.f.store_add(b2, body(530, 480, pal))
A.f.store_add(a2, { m = 1, x = 64, y = 0, z = 64, p = 0, w = 0, r = 0, s = 100 })
B.f.store_add(b2, { m = 1, x = 64, y = 0, z = 64, p = 0, w = 0, r = 0, s = 100 })
frames(40)
local h2 = host.f.store_get("5_1")
ok(count(h2, 10, 24) == 1, "two guests tell the host about one death: one body in his save")
ok(count(h2, 1, 4) == 1, "...and one stain")
ok(h2.dirty, "the host is going to save it")
host.saves = 0
host.f.flush_stores()
ok(host.saves > 0 and host.storage["B5_1_n"] ~= nil, "the host saved it")
timer = timer + 1000
B.f.sNet.ask("5_1"); deliver(); frames(5)
ok(count(b2, 10, 24) == 1 and count(b2, 1, 4) == 1, "what a guest told comes back to him once, not twice")

for i = 1, 5000 do A.f.store_add(a2, { m = 1, x = 100000 + i * 40, y = 0, z = 64, p = 0, w = 0, r = 0, s = 100 }) end
frames(3000)
ok(count(h2, 1, 4) <= 2001, "a guest who floods: the host took " .. count(h2, 1, 4) .. " of 5000 stains")

ok(A.env.gore_persist_wipe() == true, "a guest's wipe says it was only his view")
ok(A.storage["B9_1_1"] ~= nil and #host.f.store_get("9_1").list == 3007, "a guest's wipe touches neither his save nor the host's")
ok(#B.f.store_get("9_1").list == 0 and #B.f.store_get("5_1").list == 2, "nor another guest")
ok(host.env.gore_persist_wipe() == false, "the host's wipe")
deliver()
ok(#B.f.store_get("5_1").list == 0, "the host's wipe reaches the guests")
ok(B.chat[#B.chat] ~= nil and B.chat[#B.chat]:find("host wiped") ~= nil, "...and they are told")
ok(host.storage["B5_1_n"] == nil, "the host's save is wiped")
ok(A.storage["B9_1_1"] ~= nil, "the guests' own saves still are not")

local solo = make_game("solo", true, 0, {})
solo.storage["B9_1_n"] = "1"
solo.storage["B9_1_1"] = "1,7777,0,7777,0,0,0,100;10,7000,0,7000,0,0,0,100,5,3,100,0,189"
local ss = solo.f.store_get("9_1")
ok(#ss.list == 2, "a host reads his own save")
solo.f.store_add(ss, body(1, 1, pal))
solo.f.flush_stores()
ok(solo.storage["B9_1_1"]:find(pal, 1, true) ~= nil, "...and writes it")
print("ALL OK")
