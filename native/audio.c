/* TinySoundFont first-run sample renderer. No game resources are embedded. */
#ifdef XENZIA_FREESTANDING
typedef __SIZE_TYPE__ size_t;
extern void *malloc(size_t), *realloc(void *, size_t);
extern void free(void *);
extern void *memcpy(void *, const void *, size_t), *memset(void *, int, size_t);
extern double pow(double, double), log(double), tan(double), log10(double), sqrt(double);
extern float powf(float, float), expf(float), sqrtf(float);
#define TSF_MALLOC malloc
#define TSF_REALLOC realloc
#define TSF_FREE free
#define TSF_MEMCPY memcpy
#define TSF_MEMSET memset
#define TSF_POW pow
#define TSF_POWF powf
#define TSF_EXPF expf
#define TSF_LOG log
#define TSF_TAN tan
#define TSF_LOG10 log10
#define TSF_SQRT sqrt
#define TSF_SQRTF sqrtf
#endif
#define TSF_NO_STDIO
#define TSF_STATIC
#define TSF_IMPLEMENTATION
#include "../audio-source/tsf.h"
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

EXPORT int xenzia_render(const void *bank, int bank_size, int program, int note,
                        int milliseconds, short *output, int capacity) {
    if (!bank || bank_size <= 0 || !output || capacity < 1 || milliseconds < 0 || milliseconds > 5000)
        return -1;
    tsf *font = tsf_load_memory(bank, bank_size);
    if (!font) return -2;
    tsf_set_output(font, TSF_MONO, 22050, 0.0f);
    tsf_set_volume(font, 1.0f);
    int preset = tsf_get_presetindex(font, 0, program);
    if (preset < 0) { tsf_close(font); return -3; }
    tsf_note_on(font, preset, note, 100.0f / 127.0f);
    int written = 0, remaining = (22050 * milliseconds + 500) / 1000;
    while (remaining > 0) {
        int count = remaining > 256 ? 256 : remaining;
        if (written + count > capacity) { tsf_close(font); return -4; }
        tsf_render_short(font, output + written, count, 0);
        written += count; remaining -= count;
    }
    tsf_note_off(font, preset, note);
    for (int count = 0; count < 22050 * 5; count += 256) {
        if (written + 256 > capacity) { tsf_close(font); return -4; }
        tsf_render_short(font, output + written, 256, 0);
        written += 256;
        if (!tsf_active_voice_count(font)) break;
    }
    tsf_close(font);
    return written;
}

#include "graphics.c"
