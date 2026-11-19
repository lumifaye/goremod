-- Run from repo root with Lua 5.3.
local function boot(os, vr)
    local hooks, cmds, msgs, pulses = {}, {}, {}, 0
    local m = {playerIndex=0, health=0x280, action=1, numCoins=0,numStars=2,floorHeight=0,controller={buttonDown=0,buttonPressed=0},vel={y=0}, pos={x=0,y=0,z=0}, waterLevel=120}
    local env = setmetatable({HOOK_MARIO_UPDATE=1,HOOK_UPDATE=2,HOOK_ON_WARP=3,L_TRIG=1,U_JPAD=2,ACT_FLAG_AIR=4,ACT_FLAG_SWIMMING=1,
        gMarioStates={[0]=m}, MAX_PLAYERS=2, gNetworkPlayers={[0]={currAreaSyncValid=true},[1]={connected=false}},
        get_os_name=function() return os end, vr_net_state=vr,
        hook_event=function(k,f) hooks[k]=f end, hook_chat_command=function(k,_,f) cmds[k]=f end,
        get_global_timer=function() return m.tick end,
        queue_rumble_data=function() pulses=pulses+1 end}, {__index=_G})
    env.djui_popup_create=function(s) table.insert(msgs,s) end
    env.djui_chat_message_create=env.djui_popup_create
    assert(loadfile('platform_features.lua','t',env))()
    return hooks,cmds,msgs,m,function() return pulses end
end
for _,os in ipairs({'Windows','Mac OSX','Linux'}) do
    local h,c,msg,m=boot(os); assert(h[1] and not c.fieldkit)
    m.tick=20; c.split('start'); m.tick=50; c.split(''); m.tick=110; c.split('stop'); assert(msg[3]=='Total 3.00s | Split 2.00s')
end
local h,c,msg,m,p=boot('Xbox 360'); h[1]({playerIndex=1}); for i=1,31 do h[1](m) end; assert(p()==2); c.fieldkit(); h[1](m); assert(p()==2)
h,c,msg,m=boot('Android'); h[1](m); h[1](m); assert(#msg==1); m.action=0; h[1](m); m.action=1; h[1](m); assert(#msg==2)
h,c,msg=boot('Wii U'); c.spotter(); assert(msg[1]=='No teammates in this area.')
local pose={0,1,1,0,0,0,0,1,0,0,0,0}; h,c,msg=boot('Android',function() return pose end); assert(not h[1]); for i=1,45 do h[2]() end; assert(#msg==1); pose[10]=100; h[2](); pose[10]=0; for i=1,15 do h[2]() end; assert(#msg==2)
h,c=boot('Unknown'); assert(not next(h) and not next(c))
h,c,msg,m,p=boot('Xbox 360'); m.health=0x880; m.action=4; m.vel.y=-55; h[1](m); m.action=0; h[1](m); h[1](m); assert(p()==1)
m.controller={buttonDown=1,buttonPressed=2}; h[1](m); assert(msg[1]=='Status: 8/8 health | 0 coins | 2 stars')
h,c,msg,m=boot('Android'); m.action=0; m.numCoins=24; h[1](m); m.numCoins=26; h[1](m); h[1](m); assert(#msg==1 and msg[1]=='Coin milestone: 25')
h,c,msg,m=boot('Wii U'); c.trail('mark'); m.pos.x=30; c.trail(''); assert(msg[2]:find('X %-30')); h[3](); c.trail(''); assert(msg[3]:find('/trail mark'))
h,c,msg=boot('Windows',function() return pose end); pose[10]=100; c.reach(); assert(msg[1]=='Hand span: 100 game units'); pose[3]=0; c.reach(); assert(msg[2]:find('Track both'))
h,c,msg,m=boot('Linux'); c.jumpstats(); m.action=4; m.vel.y=20; h[1](m); m.pos.y=50; h[1](m); m.action=0; m.pos.y=0; m.pos.x=80; h[1](m); assert(msg[2]=='Jump: 80 units across, 50 up')
print('Platform feature routing and behavior passed')
