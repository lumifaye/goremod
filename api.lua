
local baseCharModels = {
    [CT_MARIO] = {
        headless = E_MODEL_HEADLESS_MARIO,
        topless = E_MODEL_TOPLESS_MARIO,
        gold = E_MODEL_GOLD_MARIO
    },
    [CT_LUIGI] = {
        headless = E_MODEL_HEADLESS_LUIGI,
        topless = E_MODEL_TOPLESS_LUIGI,
        gold = E_MODEL_GOLD_LUIGI
    },
    [CT_TOAD] = {
        headless = E_MODEL_HEADLESS_TOAD,
        topless = E_MODEL_TOPLESS_TOAD,
        gold = E_MODEL_GOLD_TOAD
    },
    [CT_WALUIGI] = {
        headless = E_MODEL_HEADLESS_WALUIGI,
        topless = E_MODEL_TOPLESS_WALUIGI,
        gold = E_MODEL_GOLD_WALUIGI
    },
    [CT_WARIO] = {
        headless = E_MODEL_HEADLESS_WARIO,
        topless = E_MODEL_TOPLESS_WARIO,
        gold = E_MODEL_GOLD_WARIO
    }
}
local goldModels = {}
local charModels = {}

local sBaseModels = {
    [E_MODEL_MARIO] = true, [E_MODEL_LUIGI] = true, [E_MODEL_TOAD_PLAYER] = true,
    [E_MODEL_WALUIGI] = true, [E_MODEL_WARIO] = true,
}

local function cs_api()
    if not _G.charSelectExists then return nil end
    local cs = _G.charSelect
    if type(cs) ~= "table" or type(cs.gCSPlayers) ~= "table" or cs.character_get_full_table == nil then return nil end
    return cs
end

local sNameHashes = {}
local function name_hash(name)
    local h = sNameHashes[name]
    if h == nil then
        h = 5381
        for i = 1, #name do
            h = (h * 33 + string.byte(name, i)) & 0x7FFFFFFF
        end
        if h == 0 then h = 1 end
        sNameHashes[name] = h
    end
    return h
end

function gore_cs_of_player(i)
    local cs = cs_api()
    if cs == nil then return nil, nil end
    local p = cs.gCSPlayers[i]
    if type(p) ~= "table" or type(p.saveName) ~= "string" then return nil, nil end
    return name_hash(p.saveName), math.tointeger(tonumber(p.currAlt) or 1) or 1
end

function gore_cs_model(hash, costume)
    if hash == nil then return nil end
    local cs = cs_api()
    if cs == nil then return nil end
    local ok, characters = pcall(cs.character_get_full_table)
    if not ok or type(characters) ~= "table" then return nil end
    for c = 0, #characters do
        local character = characters[c]
        if type(character) == "table" and type(character.saveName) == "string"
        and name_hash(character.saveName) == hash then
            local look = character[costume or 1] or character[1]
            return type(look) == "table" and look.model or nil
        end
    end
    return nil
end

function gore_cs_cap_model(hash, costume)
    local model = gore_cs_model(hash, costume)
    if model == nil or sBaseModels[model] then return nil end
    local cs = cs_api()
    if cs == nil or cs.character_get_caps == nil then return nil end
    local ok, caps = pcall(cs.character_get_caps, model)
    if not ok or type(caps) ~= "table" then return nil end
    local cap = caps.normal
    if cap == nil or cap == E_MODEL_NONE or cap == E_MODEL_ERROR_MODEL then return nil end
    return cap
end

function gore_cs_own_model(i)
    local model = gore_cs_model(gore_cs_of_player(i))
    if model == nil or sBaseModels[model] then return nil end
    return model
end

_G.GoreHMApi = {
    register_character_models = function (models)
    end,
    get_char_models = function (m)
        local base = baseCharModels[m.character.type] or baseCharModels[CT_MARIO]
        if gore_cs_own_model(m.playerIndex) ~= nil then
            return { gold = base.gold }
        end
        return base
    end
}