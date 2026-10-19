/* Batch original canvas API calls without crossing the Python FFI per pixel.
 * No game code, drawing algorithm, font, bitmap or audio is implemented here.
 * Commands are replayed by the same Pillow canvas, in the same order.
 */
#ifdef XENZIA_FREESTANDING
typedef __UINT32_TYPE__ uint32_t;
typedef __UINT64_TYPE__ uint64_t;
typedef __INT32_TYPE__ int32_t;
extern void *calloc(size_t,size_t);
#else
#include <stdint.h>
#include <stdlib.h>
#include <stddef.h>
#endif
#ifndef EXPORT
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
#endif
#define CAPACITY 16384
#define HOST_BASE 0x4000000u
typedef int (*ReadReg)(void *, int, void *);
typedef int (*WriteReg)(void *, int, const void *);
typedef int (*ReadMem)(void *, uint64_t, void *, size_t);
typedef int (*WriteMem)(void *, uint64_t, const void *, size_t);
typedef int (*Stop)(void *);
typedef struct {int32_t index, lr, v[4];} Command;
typedef struct {uint32_t address,size;} Block;
typedef struct {
    ReadReg read; WriteReg write; ReadMem mem; WriteMem put; Stop stop;
    uint32_t color, bg; int count, error;
    uint32_t heap;int allocated,available;
    Block blocks[4096],freeblocks[4096];
    unsigned char zero[0x20000];
    Command commands[CAPACITY];
} Graphics;
EXPORT void *xenzia_gfx_create(void *read, void *write, void *mem, void *put, void *stop) {
    Graphics *g=calloc(1,sizeof(Graphics));
    if(g){g->read=(ReadReg)read;g->write=(WriteReg)write;g->mem=(ReadMem)mem;g->put=(WriteMem)put;g->stop=(Stop)stop;}
    return g;
}
EXPORT void xenzia_gfx_destroy(void *context){free(context);}
EXPORT void xenzia_gfx_state(void *context,uint32_t color,uint32_t bg){
    Graphics *g=context;g->color=color;g->bg=bg;
}
EXPORT void *xenzia_gfx_commands(void *context){return ((Graphics*)context)->commands;}
EXPORT int xenzia_gfx_count(void *context){Graphics *g=context;return g->error ? -1 : g->count;}
EXPORT void xenzia_gfx_clear(void *context){((Graphics*)context)->count=0;}
EXPORT int xenzia_heap_import(void *context,uint32_t heap,int count,const Block *blocks,int freecount,const Block *freeblocks){
    Graphics *g=context;if(count<0||count>4096||freecount<0||freecount>4096)return -1;
    g->heap=heap;g->allocated=count;g->available=freecount;
    for(int i=0;i<count;i++)g->blocks[i]=blocks[i];
    for(int i=0;i<freecount;i++)g->freeblocks[i]=freeblocks[i];
    return 0;
}
EXPORT uint32_t xenzia_heap_export(void *context,int *count,Block *blocks,int *freecount,Block *freeblocks){
    Graphics *g=context;*count=g->allocated;*freecount=g->available;
    for(int i=0;i<g->allocated;i++)blocks[i]=g->blocks[i];
    for(int i=0;i<g->available;i++)freeblocks[i]=g->freeblocks[i];
    return g->heap;
}
EXPORT void xenzia_heap_hook(void *uc,uint64_t address,uint32_t size,void *context){
    (void)size;Graphics *g=context;uint32_t argument=0,lr=0,result=0;
    if(g->read(uc,67,&argument)||g->read(uc,10,&lr))goto fail;
    if((address-HOST_BASE)/16==7){
        uint32_t n=(argument+7)&~7u;if(n<16)n=16;
        if(argument>0x20000||g->allocated>=4096)goto fail;
        result=g->heap;int found=0;
        for(int i=0;i<g->available;i++)if(g->freeblocks[i].size>=n){
            Block *b=&g->freeblocks[i];result=b->address;
            b->address+=n;b->size-=n;
            if(!b->size){for(int j=i;j<g->available-1;j++)g->freeblocks[j]=g->freeblocks[j+1];g->available--;}
            if(g->put(uc,result,g->zero,n))goto fail;
            found=1;break;
        }
        if(!found){if(result+n>0x2200000u)goto fail;g->heap+=n;}
        g->blocks[g->allocated++]=(Block){result,n};
    }else{
        int found=-1;
        for(int i=0;i<g->allocated;i++)if(g->blocks[i].address==argument){found=i;break;}
        if(found>=0){
            if(g->available>=4096)goto fail;
            Block b=g->blocks[found];
            for(int j=found;j<g->allocated-1;j++)g->blocks[j]=g->blocks[j+1];g->allocated--;
            int i=g->available;
            while(i>0&&g->freeblocks[i-1].address>b.address){g->freeblocks[i]=g->freeblocks[i-1];i--;}
            g->freeblocks[i]=b;g->available++;
            int out=0;
            for(int j=0;j<g->available;j++){
                b=g->freeblocks[j];
                if(out&&g->freeblocks[out-1].address+g->freeblocks[out-1].size==b.address)g->freeblocks[out-1].size+=b.size;
                else g->freeblocks[out++]=b;
            }
            g->available=out;
        }
    }
    if(g->write(uc,66,&result)||g->write(uc,11,&lr))goto fail;
    return;
fail:g->error=1;g->stop(uc);
}
EXPORT void xenzia_gfx_hook(void *uc,uint64_t address,uint32_t size,void *context){
    (void)size;Graphics *g=context;
    int index=(int)((address-HOST_BASE)/16),n=0;uint32_t result=0,lr=0;
    if(g->read(uc,10,&lr)){g->error=1;g->stop(uc);return;} /* ARM LR */
    switch(index){
        case 258:result=96;break;case 259:result=65;break;
        case 261:case 262:n=1;break;case 263:result=g->color;break;
        case 264:result=g->bg;break;case 266:n=2;break;
        case 268:case 269:case 270:n=4;break;
    }
    if(n){
        if(g->count==CAPACITY){g->error=1;g->stop(uc);return;}
        Command *c=&g->commands[g->count++];c->index=index;c->lr=lr;
        for(int i=0;i<n&&i<3;i++)if(g->read(uc,67+i,&c->v[i])){g->error=1;g->stop(uc);return;} /* R1..R3 */
        if(n==4){uint32_t sp=0;unsigned char value[4];
            if(g->read(uc,12,&sp)||g->mem(uc,sp,value,4)){g->error=1;g->stop(uc);return;}
            c->v[3]=(int32_t)((uint32_t)value[0]<<24|(uint32_t)value[1]<<16|(uint32_t)value[2]<<8|value[3]);
        }
        if(index==261)g->color=(uint32_t)c->v[0];
        if(index==262)g->bg=(uint32_t)c->v[0];
    }
    if(g->write(uc,66,&result)||g->write(uc,11,&lr)){g->error=1;g->stop(uc);} /* R0, PC */
}
