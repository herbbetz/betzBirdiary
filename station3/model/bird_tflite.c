/*
 bird_tflite.c

 Minimal TensorFlow Lite inference wrapper.

 Features
 --------
 - direct access to input tensor memory (zero-copy input)
 - supports uint8 / int8 / float32 outputs
 - exposes output size to Python
 - small API suitable for ctypes

 Compile
 -------
 gcc -O3 -fPIC -shared bird_tflite.c -o libbird_tflite.so -ltensorflow-lite
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "tensorflow/lite/c/c_api.h"


typedef struct
{
    TfLiteModel* model;
    TfLiteInterpreterOptions* options;
    TfLiteInterpreter* interpreter;

} BirdModel;



// ----------------------------------------------------------
// load model
// ----------------------------------------------------------

void* bird_model_load(
    const char* path,
    int threads
)
{
    BirdModel* m = calloc(1,sizeof(BirdModel));

    m->model = TfLiteModelCreateFromFile(path);

    if(!m->model)
        return NULL;

    m->options = TfLiteInterpreterOptionsCreate();

    TfLiteInterpreterOptionsSetNumThreads(
        m->options,
        threads
    );

    m->interpreter =
        TfLiteInterpreterCreate(
            m->model,
            m->options
        );

    if(!m->interpreter)
        return NULL;

    if(TfLiteInterpreterAllocateTensors(m->interpreter)
        != kTfLiteOk)
        return NULL;

    return m;
}



 // ----------------------------------------------------------
 // get tensor information
 // ----------------------------------------------------------

int bird_model_input_info(
    void* handle,
    int* width,
    int* height,
    int* channels,
    int* layout,
    int* dtype
)
{
    BirdModel* m = (BirdModel*)handle;

    TfLiteTensor* t =
        TfLiteInterpreterGetInputTensor(
            m->interpreter,
            0
        );

    int dims = TfLiteTensorNumDims(t);

    if(dims != 4)
        return 0;

    int d0 = TfLiteTensorDim(t,0);
    int d1 = TfLiteTensorDim(t,1);
    int d2 = TfLiteTensorDim(t,2);
    int d3 = TfLiteTensorDim(t,3);

    /*
    Detect layout

    NHWC = [1,H,W,C]
    NCHW = [1,C,H,W]
    */

    if(d1 <= 4)
    {
        // NCHW

        *layout   = 1;
        *channels = d1;
        *height   = d2;
        *width    = d3;
    }
    else
    {
        // NHWC

        *layout   = 0;
        *height   = d1;
        *width    = d2;
        *channels = d3;
    }

    TfLiteType type = TfLiteTensorType(t);

    if(type == kTfLiteUInt8)
        *dtype = 0;
    else
        *dtype = 1;

    return 1;
}



 // ----------------------------------------------------------
 // return direct input buffer
 // ----------------------------------------------------------

void* bird_model_input_buffer(void* handle)
{
    BirdModel* m = (BirdModel*)handle;

    TfLiteTensor* t =
        TfLiteInterpreterGetInputTensor(
            m->interpreter,
            0
        );

    return TfLiteTensorData(t);
}



 // ----------------------------------------------------------
 // output classes
 // ----------------------------------------------------------

int bird_model_output_size(void* handle)
{
    BirdModel* m = (BirdModel*)handle;

    const TfLiteTensor* t =
        TfLiteInterpreterGetOutputTensor(
            m->interpreter,
            0
        );

    return TfLiteTensorDim(t,1);
}



 // ----------------------------------------------------------
 // inference
 // ----------------------------------------------------------

int bird_model_infer(
    void* handle,
    void* output
)
{
    BirdModel* m = (BirdModel*)handle;

    if(TfLiteInterpreterInvoke(m->interpreter)
        != kTfLiteOk)
        return 0;

    const TfLiteTensor* out =
        TfLiteInterpreterGetOutputTensor(
            m->interpreter,
            0
        );

    int size =
        TfLiteTensorByteSize(out);

    memcpy(
        output,
        TfLiteTensorData(out),
        size
    );

    return 1;
}



 // ----------------------------------------------------------
 // free
 // ----------------------------------------------------------

void bird_model_free(void* handle)
{
    BirdModel* m = (BirdModel*)handle;

    if(!m) return;

    TfLiteInterpreterDelete(m->interpreter);
    TfLiteInterpreterOptionsDelete(m->options);
    TfLiteModelDelete(m->model);

    free(m);
}