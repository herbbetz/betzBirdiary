/*
 sndclass.c

 TensorFlow Lite C API wrapper for BirdNET-style waveform models:
   input:  float32 [1, N] (e.g. N = 144000 = 3 s @ 48 kHz mono)
   output: float32 logits or probabilities [1, num_classes]

 Fills input from WAV: mono, PCM s16le, 48000 Hz (typical ffmpeg export).

 Compile (Linux / Raspberry Pi OS)
 ---------------------------------
 gcc -O3 -fPIC -shared sndclass.c -o libsndclass.so -ltensorflow-lite -lm
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <tensorflow/lite/c/c_api.h>

typedef struct {

    TfLiteModel* model;
    TfLiteInterpreterOptions* options;
    TfLiteInterpreter* interpreter;

    TfLiteTensor* input_tensor;
    const TfLiteTensor* output_tensor;

    int input_num_elements;
    int output_num_elements;

} SndModel;

static int tensor_total_elements(const TfLiteTensor* t)
{
    int n = TfLiteTensorNumDims(t);
    int total = 1;
    for (int i = 0; i < n; i++)
        total *= TfLiteTensorDim(t, i);
    return total;
}

void* snd_model_load(const char* model_path, int threads)
{
    SndModel* m = calloc(1, sizeof(SndModel));
    if (!m)
        return NULL;

    m->model = TfLiteModelCreateFromFile(model_path);
    if (!m->model)
        goto fail;

    m->options = TfLiteInterpreterOptionsCreate();
    if (!m->options)
        goto fail;
    TfLiteInterpreterOptionsSetNumThreads(m->options, threads);

    m->interpreter = TfLiteInterpreterCreate(m->model, m->options);
    if (!m->interpreter)
        goto fail;

    if (TfLiteInterpreterAllocateTensors(m->interpreter) != kTfLiteOk)
        goto fail;

    m->input_tensor = TfLiteInterpreterGetInputTensor(m->interpreter, 0);
    m->output_tensor = TfLiteInterpreterGetOutputTensor(m->interpreter, 0);

    if (!m->input_tensor || !m->output_tensor)
        goto fail;

    if (TfLiteTensorType(m->input_tensor) != kTfLiteFloat32) {
        fprintf(stderr, "snd_model_load: input must be float32\n");
        goto fail;
    }

    int idims = TfLiteTensorNumDims(m->input_tensor);
    if (idims != 2) {
        fprintf(stderr, "snd_model_load: expected 2D input [batch, samples], got %d dims\n", idims);
        goto fail;
    }

    if (TfLiteTensorDim(m->input_tensor, 0) != 1) {
        fprintf(stderr, "snd_model_load: batch dim must be 1\n");
        goto fail;
    }

    m->input_num_elements = tensor_total_elements(m->input_tensor);
    m->output_num_elements = tensor_total_elements(m->output_tensor);

    if (m->input_num_elements <= 0 || m->output_num_elements <= 0) {
        fprintf(stderr, "snd_model_load: invalid tensor sizes\n");
        goto fail;
    }

    return m;

fail:
    if (m->interpreter)
        TfLiteInterpreterDelete(m->interpreter);
    if (m->options)
        TfLiteInterpreterOptionsDelete(m->options);
    if (m->model)
        TfLiteModelDelete(m->model);
    free(m);
    return NULL;
}

void snd_model_input_samples(void* handle, int* out_batch, int* out_samples)
{
    SndModel* m = (SndModel*)handle;
    if (!m || !out_batch || !out_samples)
        return;
    *out_batch = TfLiteTensorDim(m->input_tensor, 0);
    *out_samples = TfLiteTensorDim(m->input_tensor, 1);
}

int snd_model_input_elements(void* handle)
{
    SndModel* m = (SndModel*)handle;
    return m ? m->input_num_elements : 0;
}

int snd_model_output_size(void* handle)
{
    SndModel* m = (SndModel*)handle;
    return m ? m->output_num_elements : 0;
}

void* snd_model_input_buffer(void* handle)
{
    SndModel* m = (SndModel*)handle;
    return m ? TfLiteTensorData(m->input_tensor) : NULL;
}

int snd_model_infer(void* handle, void* output_buffer)
{
    SndModel* m = (SndModel*)handle;
    if (!m || !output_buffer)
        return -1;

    if (TfLiteInterpreterInvoke(m->interpreter) != kTfLiteOk)
        return -1;

    int size = m->output_num_elements;
    float* dst = (float*)output_buffer;

    TfLiteType type = TfLiteTensorType(m->output_tensor);

    if (type == kTfLiteFloat32) {
        const float* src = TfLiteTensorData(m->output_tensor);
        memcpy(dst, src, (size_t)size * sizeof(float));
        return 0;
    }

    if (type == kTfLiteUInt8) {
        const uint8_t* src = TfLiteTensorData(m->output_tensor);
        TfLiteQuantizationParams q = TfLiteTensorQuantizationParams(m->output_tensor);
        for (int i = 0; i < size; i++)
            dst[i] = ((float)src[i] - q.zero_point) * q.scale;
        return 0;
    }

    if (type == kTfLiteInt8) {
        const int8_t* src = TfLiteTensorData(m->output_tensor);
        TfLiteQuantizationParams q = TfLiteTensorQuantizationParams(m->output_tensor);
        for (int i = 0; i < size; i++)
            dst[i] = ((float)src[i] - q.zero_point) * q.scale;
        return 0;
    }

    fprintf(stderr, "snd_model_infer: unsupported output type\n");
    return -1;
}

void snd_model_free(void* handle)
{
    SndModel* m = (SndModel*)handle;
    if (!m)
        return;
    if (m->interpreter)
        TfLiteInterpreterDelete(m->interpreter);
    if (m->options)
        TfLiteInterpreterOptionsDelete(m->options);
    if (m->model)
        TfLiteModelDelete(m->model);
    free(m);
}

/* Read mono PCM s16le from WAV; fill dst[0..expect-1] with float32 in [-1,1]. */
int snd_wav_fill_input(const char* wav_path, float* dst, int expect_samples)
{
    if (!wav_path || !dst || expect_samples <= 0)
        return -1;

    FILE* f = fopen(wav_path, "rb");
    if (!f) {
        perror("snd_wav_fill_input fopen");
        return -2;
    }

    char riff[4];
    uint32_t riff_size;
    char wave[4];
    if (fread(riff, 1, 4, f) != 4 || memcmp(riff, "RIFF", 4) != 0) {
        fprintf(stderr, "snd_wav_fill_input: not RIFF\n");
        fclose(f);
        return -3;
    }
    if (fread(&riff_size, 4, 1, f) != 1) {
        fclose(f);
        return -3;
    }
    if (fread(wave, 1, 4, f) != 4 || memcmp(wave, "WAVE", 4) != 0) {
        fprintf(stderr, "snd_wav_fill_input: not WAVE\n");
        fclose(f);
        return -3;
    }

    uint16_t audio_format = 0;
    uint16_t num_channels = 0;
    uint32_t sample_rate = 0;
    uint16_t bits_per_sample = 0;
    int fmt_ok = 0;
    uint8_t* pcm_data = NULL;
    uint32_t pcm_bytes = 0;

    while (1) {
        char cid[4];
        uint32_t csize;
        if (fread(cid, 1, 4, f) != 4)
            break;
        if (fread(&csize, 4, 1, f) != 1)
            break;

        long chunk_start = ftell(f);

        if (memcmp(cid, "fmt ", 4) == 0) {
            if (csize < 16) {
                fprintf(stderr, "snd_wav_fill_input: fmt chunk too small\n");
                free(pcm_data);
                fclose(f);
                return -4;
            }
            if (fread(&audio_format, 2, 1, f) != 1
                || fread(&num_channels, 2, 1, f) != 1
                || fread(&sample_rate, 4, 1, f) != 1) {
                free(pcm_data);
                fclose(f);
                return -4;
            }
            uint32_t byte_rate;
            uint16_t block_align;
            if (fread(&byte_rate, 4, 1, f) != 1
                || fread(&block_align, 2, 1, f) != 1
                || fread(&bits_per_sample, 2, 1, f) != 1) {
                free(pcm_data);
                fclose(f);
                return -4;
            }
            fmt_ok = 1;
        } else if (memcmp(cid, "data", 4) == 0) {
            pcm_data = malloc(csize);
            if (!pcm_data) {
                fclose(f);
                return -5;
            }
            if (fread(pcm_data, 1, csize, f) != csize) {
                free(pcm_data);
                fclose(f);
                return -6;
            }
            pcm_bytes = csize;
            break;
        }

        long skip = (long)csize;
        if (csize & 1u)
            skip++;
        if (fseek(f, chunk_start + skip, SEEK_SET) != 0) {
            fprintf(stderr, "snd_wav_fill_input: seek error\n");
            free(pcm_data);
            fclose(f);
            return -7;
        }
    }

    fclose(f);

    if (!fmt_ok || !pcm_data) {
        fprintf(stderr, "snd_wav_fill_input: missing fmt or data chunk\n");
        free(pcm_data);
        return -8;
    }

    if (audio_format != 1) {
        fprintf(stderr, "snd_wav_fill_input: need PCM format 1, got %u\n", (unsigned)audio_format);
        free(pcm_data);
        return -9;
    }
    if (num_channels != 1) {
        fprintf(stderr, "snd_wav_fill_input: need mono (1 channel), got %u\n", (unsigned)num_channels);
        free(pcm_data);
        return -10;
    }
    if (sample_rate != 48000u) {
        fprintf(stderr, "snd_wav_fill_input: need 48000 Hz sample rate, got %u\n", (unsigned)sample_rate);
        free(pcm_data);
        return -11;
    }
    if (bits_per_sample != 16) {
        fprintf(stderr, "snd_wav_fill_input: need 16-bit PCM, got %u\n", (unsigned)bits_per_sample);
        free(pcm_data);
        return -12;
    }

    size_t num_samples = pcm_bytes / sizeof(int16_t);
    const int16_t* s = (const int16_t*)pcm_data;

    size_t copy = num_samples;
    if (copy > (size_t)expect_samples)
        copy = (size_t)expect_samples;

    for (size_t i = 0; i < copy; i++)
        dst[i] = (float)s[i] / 32768.0f;

    for (size_t i = copy; i < (size_t)expect_samples; i++)
        dst[i] = 0.0f;

    free(pcm_data);
    return 0;
}

int snd_wav_fill_model_input(void* handle, const char* wav_path)
{
    SndModel* m = (SndModel*)handle;
    if (!m)
        return -1;
    float* buf = TfLiteTensorData(m->input_tensor);
    if (!buf)
        return -1;
    int n = TfLiteTensorDim(m->input_tensor, 1);
    return snd_wav_fill_input(wav_path, buf, n);
}
