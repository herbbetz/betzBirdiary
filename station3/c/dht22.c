/*
 * C processing of 40-bit decoding of edges collected in Python
 * Build:
 * gcc -shared -o libdht22.so -fPIC dht22.c
 */
#include <stdint.h>

int decode_dht22_edges(uint64_t *edges, int n_edges, float *temperature, float *humidity)
{
    if(n_edges < 80) return -1; // too few edges

    uint8_t data[5] = {0};
    int bit = 0;
    const int THRESHOLD = 55; // µs, pulse width threshold for '1'

    for(int i = 2; i < n_edges && bit < 40; i += 2)
    {
        uint64_t pulse = edges[i] - edges[i-1];
        if(pulse > THRESHOLD) data[bit/8] |= (1 << (7-(bit%8)));
        bit++;
    }

    uint8_t sum = data[0]+data[1]+data[2]+data[3];
    if(sum != data[4]) return -2; // checksum error

    *humidity = ((data[0]<<8)|data[1]) / 10.0;

    int16_t t = ((data[2]&0x7F)<<8)|data[3];
    *temperature = t / 10.0;
    if(data[2] & 0x80) *temperature = -*temperature;

    return 0;
}
