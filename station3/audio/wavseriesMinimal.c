/* produce wav clips separated by silence
mic and headphone card default set in /etc/asound.conf
testmic.py found 44100 as rate accepted by my mic
sudo apt install libasound2-dev
gcc -o wavseries wavseries.c -lasound -lm
./wavseries
*/
#include <stdio.h>
#include <stdlib.h>
#include <alsa/asoundlib.h>
#include <signal.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define DEVICE "hw:3,0"       // your USB mic
#define RATE 48000
#define CHANNELS 1
#define FORMAT SND_PCM_FORMAT_S16_LE
#define CHUNK 1024             // frames per read
#define SILENCE_THRESHOLD 500  // RMS threshold for silence
#define SILENCE_FRAMES (RATE*2) // 2 seconds of silence to split

volatile sig_atomic_t stop = 0;

void handle_sigint(int sig) {
    stop = 1;
}

typedef struct {
    FILE *file;
    int index;
    int frames_written;
} wav_file_t;

// write WAV header placeholder (will update sizes later)
void write_wav_header(FILE *f, int sample_rate, int channels) {
    uint32_t datasize = 0xFFFFFFFF;  // placeholder
    uint16_t bits = 16;
    fwrite("RIFF",1,4,f);
    fwrite(&datasize,4,1,f);
    fwrite("WAVE",1,4,f);
    fwrite("fmt ",1,4,f);
    uint32_t fmt_size = 16;
    fwrite(&fmt_size,4,1,f);
    uint16_t audio_format = 1;
    fwrite(&audio_format,2,1,f);
    fwrite(&channels,2,1,f);
    fwrite(&sample_rate,4,1,f);
    uint32_t byte_rate = sample_rate * channels * bits/8;
    fwrite(&byte_rate,4,1,f);
    uint16_t block_align = channels * bits/8;
    fwrite(&block_align,2,1,f);
    fwrite(&bits,2,1,f);
    fwrite("data",1,4,f);
    fwrite(&datasize,4,1,f);
}

void update_wav_header(FILE *f) {
    long filesize = ftell(f);
    uint32_t datasize = filesize - 44;
    fseek(f,4,SEEK_SET);
    uint32_t riffsize = filesize - 8;
    fwrite(&riffsize,4,1,f);
    fseek(f,40,SEEK_SET);
    fwrite(&datasize,4,1,f);
}

int main() {
    snd_pcm_t *pcm;
    snd_pcm_hw_params_t *params;
    int err;

    signal(SIGINT, handle_sigint);

    if ((err = snd_pcm_open(&pcm, DEVICE, SND_PCM_STREAM_CAPTURE, 0)) < 0) {
        fprintf(stderr, "Cannot open PCM device: %s\n", snd_strerror(err));
        return 1;
    }

    snd_pcm_hw_params_malloc(&params);
    snd_pcm_hw_params_any(pcm, params);
    snd_pcm_hw_params_set_access(pcm, params, SND_PCM_ACCESS_RW_INTERLEAVED);
    snd_pcm_hw_params_set_format(pcm, params, FORMAT);
    snd_pcm_hw_params_set_channels(pcm, params, CHANNELS);
    unsigned int rate = RATE;
    snd_pcm_hw_params_set_rate_near(pcm, params, &rate, 0);
    snd_pcm_hw_params(pcm, params);
    snd_pcm_hw_params_free(params);
    snd_pcm_prepare(pcm);

    int16_t buffer[CHUNK];
    wav_file_t wav = {NULL, 1, 0};
    int silence_counter = 0;
    int recording = 0;

    printf("Listening for sound... Press Ctrl+C to exit.\n");

    while (!stop) {
        int frames = snd_pcm_readi(pcm, buffer, CHUNK);
        if (frames < 0) {
            frames = snd_pcm_recover(pcm, frames, 0);
        }
        if (frames < 0) {
            fprintf(stderr, "PCM read error: %s\n", snd_strerror(frames));
            break;
        }

        // calculate RMS
        double sum = 0.0;
        for(int i=0;i<frames*CHANNELS;i++) {
            sum += buffer[i]*buffer[i];
        }
        double rms = sqrt(sum/(frames*CHANNELS));

        if(rms > SILENCE_THRESHOLD) {
            if(!recording) {
                char fname[64];
                sprintf(fname,"%d.wav",wav.index++);
                wav.file = fopen(fname,"wb");
                if(!wav.file) {
                    perror("fopen");
                    break;
                }
                write_wav_header(wav.file, RATE, CHANNELS);
                wav.frames_written = 0;
                recording = 1;
                silence_counter = 0;
                printf("Sound detected, recording to %d.wav\n", wav.index-1);
            }
            fwrite(buffer, sizeof(int16_t), frames*CHANNELS, wav.file);
            wav.frames_written += frames;
            silence_counter = 0;
        } else if(recording) {
            silence_counter += frames;
            fwrite(buffer, sizeof(int16_t), frames*CHANNELS, wav.file);
            wav.frames_written += frames;
            if(silence_counter >= SILENCE_FRAMES) {
                // end recording
                update_wav_header(wav.file);
                fclose(wav.file);
                wav.file = NULL;
                recording = 0;
                silence_counter = 0;
                printf("Saved clip, waiting for next sound...\n");
            }
        }
    }

    // finalize last recording if needed
    if(recording && wav.file) {
        update_wav_header(wav.file);
        fclose(wav.file);
        printf("Saved last clip before exit.\n");
    }

    snd_pcm_close(pcm);
    printf("Exiting gracefully.\n");
    return 0;
}