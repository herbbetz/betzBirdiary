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
#include <stdint.h>
#include <string.h>

#include <tensorflow/lite/c/c_api.h>


/* --------------------------------------------------
   internal model structure
   -------------------------------------------------- */

typedef struct
{
    TfLiteModel* model;
    TfLiteInterpreterOptions* options;
    TfLiteInterpreter* interpreter;

    TfLiteTensor* input;
    const TfLiteTensor* output;

    int input_width;
    int input_height;
    int input_channels;

    int output_size;

    TfLiteType input_type;
    TfLiteType output_type;

} BirdModel;


/* --------------------------------------------------
   load model
   -------------------------------------------------- */

void* bird_model_load(const char* model_path, int threads)
{
    BirdModel* m = calloc(1,sizeof(BirdModel));

    if(!m)
        return NULL;

    /* load model file */

    m->model = TfLiteModelCreateFromFile(model_path);

    if(!m->model)
        return NULL;

    /* create interpreter options */

    m->options = TfLiteInterpreterOptionsCreate();

    TfLiteInterpreterOptionsSetNumThreads(
        m->options,
        threads
    );

    /* create interpreter */

    m->interpreter =
        TfLiteInterpreterCreate(
            m->model,
            m->options
        );

    if(!m->interpreter)
        return NULL;

    /* allocate tensors */

    if(TfLiteInterpreterAllocateTensors(
        m->interpreter
    ) != kTfLiteOk)
        return NULL;

    /* obtain tensors */

    m->input =
        TfLiteInterpreterGetInputTensor(
            m->interpreter,
            0
        );

    m->output =
        TfLiteInterpreterGetOutputTensor(
            m->interpreter,
            0
        );

    /* store tensor types */

    m->input_type  = TfLiteTensorType(m->input);
    m->output_type = TfLiteTensorType(m->output);

    /* read input dimensions */

    m->input_height =
        TfLiteTensorDim(m->input,1);

    m->input_width =
        TfLiteTensorDim(m->input,2);

    m->input_channels =
        TfLiteTensorDim(m->input,3);

    /* read output vector size */

    m->output_size =
        TfLiteTensorDim(m->output,1);

    return m;
}


/* --------------------------------------------------
   query input tensor shape
   -------------------------------------------------- */

int bird_model_input_size(
    void* handle,
    int* width,
    int* height,
    int* channels)
{
    BirdModel* m = (BirdModel*)handle;

    *width  = m->input_width;
    *height = m->input_height;
    *channels = m->input_channels;

    return 1;
}


/* --------------------------------------------------
   return output vector size
   -------------------------------------------------- */

int bird_model_output_size(void* handle)
{
    BirdModel* m = (BirdModel*)handle;

    return m->output_size;
}


/* --------------------------------------------------
   return pointer to input tensor memory

   Python can write image data directly here
   -------------------------------------------------- */

void* bird_model_input_buffer(void* handle)
{
    BirdModel* m = (BirdModel*)handle;

    return TfLiteTensorData(m->input);
}


/* --------------------------------------------------
   run inference
   -------------------------------------------------- */

int bird_model_infer(
    void* handle,
    float* output_buffer)
{
    BirdModel* m = (BirdModel*)handle;

    /* run interpreter */

    if(TfLiteInterpreterInvoke(
        m->interpreter
    ) != kTfLiteOk)
        return 0;

    /* read output tensor */

    size_t bytes =
        TfLiteTensorByteSize(m->output);

    void* tmp = malloc(bytes);

    if(!tmp)
        return 0;

    if(TfLiteTensorCopyToBuffer(
        m->output,
        tmp,
        bytes
    ) != kTfLiteOk)
    {
        free(tmp);
        return 0;
    }

    /* convert output to float */

    if(m->output_type == kTfLiteFloat32)
    {
        memcpy(output_buffer,tmp,bytes);
    }

    else if(m->output_type == kTfLiteUInt8)
    {
        uint8_t* p = (uint8_t*)tmp;

        for(int i=0;i<m->output_size;i++)
            output_buffer[i] =
                p[i] / 255.0f;
    }

    else if(m->output_type == kTfLiteInt8)
    {
        int8_t* p = (int8_t*)tmp;

        for(int i=0;i<m->output_size;i++)
            output_buffer[i] =
                (p[i] + 128) / 255.0f;
    }

    free(tmp);

    return m->output_size;
}


/* --------------------------------------------------
   free model
   -------------------------------------------------- */

void bird_model_free(void* handle)
{
    BirdModel* m = (BirdModel*)handle;

    if(!m)
        return;

    if(m->interpreter)
        TfLiteInterpreterDelete(
            m->interpreter
        );

    if(m->options)
        TfLiteInterpreterOptionsDelete(
            m->options
        );

    if(m->model)
        TfLiteModelDelete(
            m->model
        );

    free(m);
}