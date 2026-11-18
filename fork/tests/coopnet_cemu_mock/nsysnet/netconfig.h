#pragma once
#include <stdint.h>
typedef uint16_t NetConfInterfaceType;
struct NetConfMACAddr { uint8_t MACAddr[6]; };
enum { NET_CONF_INTERFACE_TYPE_WIFI, NET_CONF_INTERFACE_TYPE_ETHERNET };
extern "C" int netconf_init();
extern "C" int netconf_close();
extern "C" int netconf_get_if_macaddr(NetConfInterfaceType, NetConfMACAddr*);
