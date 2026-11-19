#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>
#include "xbox360_compat.h"
int main(void) {
 struct sockaddr_in a={0}; a.sin_family=AF_INET;a.sin_port=htons(34197);assert(inet_pton(AF_INET,"192.0.2.40",&a.sin_addr)==1);
 char host[32], port[8];
 assert(juice_xbox360_getnameinfo((const struct sockaddr*)&a,sizeof(a),host,sizeof(host),port,sizeof(port),NI_NUMERICHOST|NI_NUMERICSERV|NI_DGRAM)==0);
 assert(!strcmp(host,"192.0.2.40")&&!strcmp(port,"34197"));
 assert(juice_xbox360_getnameinfo((const struct sockaddr*)&a,sizeof(a),host,3,port,sizeof(port),NI_NUMERICHOST)!=0);
 assert(juice_xbox360_getnameinfo((const struct sockaddr*)&a,sizeof(a),host,sizeof(host),port,3,NI_NUMERICHOST)!=0);
 assert(juice_xbox360_getnameinfo((const struct sockaddr*)&a,1,host,sizeof(host),0,0,0)!=0);
 assert(juice_xbox360_getnameinfo((const struct sockaddr*)&a,sizeof(a),0,0,port,sizeof(port),0x40000000)!=0);
 puts("xSDK numeric IPv4 formatting shim: passed");
}
