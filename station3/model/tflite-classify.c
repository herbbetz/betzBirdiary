/*
apt install libtensorflow-lite-dev => /usr/include/tensorflow/lite/c/c_api.h, /usr/lib/libtensorflow-lite.so
apt install libjpeg62-turbo-dev
gcc tflite-classify.c -o tflite-classify -ltensorflow-lite -ljpeg -lm -lpthread -ldl
./tflite-classify test/8.jpg model0/classify.tflite model0/bird_labels_de_latin.txt

   Simple TensorFlow Lite image classifier (C API)

   Features
   --------
   - loads .tflite model
   - loads JPEG image
   - resizes to model input
   - supports float32 / uint8 / int8 models
   - prints top-5 predictions
   - prints tensor debug info
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>

#include <jpeglib.h>
#include <tensorflow/lite/c/c_api.h>

#define MAX_LABELS 2000
#define MAX_LINE   512
#define TOPK       5

/* ------------------------------------------------ */
/* label storage                                     */
/* ------------------------------------------------ */

char *labels[MAX_LABELS];
int label_count = 0;

/* ------------------------------------------------ */
/* load labels from file                             */
/* ------------------------------------------------ */

void load_labels(const char *path)
{
    FILE *f = fopen(path,"r");
    if(!f){
        perror("labels");
        exit(1);
    }

    char line[MAX_LINE];

    while(fgets(line,sizeof(line),f))
    {
        line[strcspn(line,"\n")] = 0;
        labels[label_count++] = strdup(line);
    }

    fclose(f);
}

/* ------------------------------------------------ */
/* debug helper: print tensor metadata               */
/* about ~20 lines but extremely useful              */
/* ------------------------------------------------ */

void debug_tensor(const TfLiteTensor *t,const char *name)
{
    printf("\nTensor: %s\n",name);

    printf("  type: ");
    switch(TfLiteTensorType(t))
    {
        case kTfLiteFloat32: printf("float32"); break;
        case kTfLiteUInt8:   printf("uint8"); break;
        case kTfLiteInt8:    printf("int8"); break;
        case kTfLiteInt32:   printf("int32"); break;
        default:             printf("other(%d)",TfLiteTensorType(t));
    }
    printf("\n");

    printf("  shape: ");

    int dims = TfLiteTensorNumDims(t);
    for(int i=0;i<dims;i++)
        printf("%d ",TfLiteTensorDim(t,i));
    printf("\n");

    TfLiteQuantizationParams q = TfLiteTensorQuantizationParams(t);

    printf("  quantization scale: %.6f\n",q.scale);
    printf("  quantization zero_point: %d\n",q.zero_point);
}

/* ------------------------------------------------ */
/* load JPEG using libjpeg                          */
/* ------------------------------------------------ */

unsigned char* load_jpeg(
        const char *filename,
        int *width,
        int *height,
        int *channels)
{
    FILE *fp = fopen(filename,"rb");

    if(!fp){
        perror("image");
        return NULL;
    }

    struct jpeg_decompress_struct cinfo;
    struct jpeg_error_mgr jerr;

    cinfo.err = jpeg_std_error(&jerr);
    jpeg_create_decompress(&cinfo);

    jpeg_stdio_src(&cinfo,fp);

    jpeg_read_header(&cinfo,TRUE);
    jpeg_start_decompress(&cinfo);

    *width    = cinfo.output_width;
    *height   = cinfo.output_height;
    *channels = cinfo.output_components;

    unsigned long size =
        (*width)*(*height)*(*channels);

    unsigned char *data = malloc(size);

    while(cinfo.output_scanline < cinfo.output_height)
    {
        unsigned char *row =
            data + cinfo.output_scanline*
            (*width)*(*channels);

        jpeg_read_scanlines(&cinfo,&row,1);
    }

    jpeg_finish_decompress(&cinfo);
    jpeg_destroy_decompress(&cinfo);

    fclose(fp);

    return data;
}

/* ------------------------------------------------ */
/* very simple nearest neighbour resize              */
/* ------------------------------------------------ */

void resize_nn(
    unsigned char *src,
    int sw,int sh,
    unsigned char *dst,
    int dw,int dh)
{
    for(int y=0;y<dh;y++)
    for(int x=0;x<dw;x++)
    {
        int sx = x*sw/dw;
        int sy = y*sh/dh;

        for(int c=0;c<3;c++)
            dst[(y*dw+x)*3+c] =
                src[(sy*sw+sx)*3+c];
    }
}

/* ------------------------------------------------ */
/* main program                                      */
/* ------------------------------------------------ */

int main(int argc,char **argv)
{
    if(argc < 4)
    {
        printf("Usage:\n");
        printf("%s image.jpg model.tflite labels.txt\n",
               argv[0]);
        return 1;
    }

    const char *image_path  = argv[1];
    const char *model_path  = argv[2];
    const char *labels_path = argv[3];

    load_labels(labels_path);

    /* ------------------------------------------------ */
    /* load model                                       */
    /* ------------------------------------------------ */

    TfLiteModel *model =
        TfLiteModelCreateFromFile(model_path);

    TfLiteInterpreterOptions *options =
        TfLiteInterpreterOptionsCreate();

    TfLiteInterpreterOptionsSetNumThreads(options,4);

    TfLiteInterpreter *interpreter =
        TfLiteInterpreterCreate(model,options);

    TfLiteInterpreterAllocateTensors(interpreter);

    /* ------------------------------------------------ */
    /* input tensor                                     */
    /* ------------------------------------------------ */

    TfLiteTensor *input =
        TfLiteInterpreterGetInputTensor(interpreter,0);

    int height = TfLiteTensorDim(input,1);
    int width  = TfLiteTensorDim(input,2);

    printf("\nModel info\n");
    printf("----------\n");

    debug_tensor(input,"input");

    /* ------------------------------------------------ */
    /* load image                                       */
    /* ------------------------------------------------ */

    int iw,ih,ic;

    unsigned char *img =
        load_jpeg(image_path,&iw,&ih,&ic);

    if(!img){
        printf("image load failed\n");
        return 1;
    }

    unsigned char *resized =
        malloc(width*height*3);

    resize_nn(img,iw,ih,resized,width,height);

    /* ------------------------------------------------ */
    /* copy image to tensor                             */
    /* ------------------------------------------------ */

    TfLiteTensorCopyFromBuffer(
        input,
        resized,
        width*height*3
    );

    /* ------------------------------------------------ */
    /* run inference                                    */
    /* ------------------------------------------------ */

    if(TfLiteInterpreterInvoke(interpreter)!=kTfLiteOk)
    {
        printf("inference failed\n");
        return 1;
    }

    /* ------------------------------------------------ */
    /* output tensor                                    */
    /* ------------------------------------------------ */

    const TfLiteTensor *output =
        TfLiteInterpreterGetOutputTensor(interpreter,0);

    debug_tensor(output,"output");

    int num_classes = TfLiteTensorDim(output,1);

    printf("\nNumber of classes: %d\n",num_classes);

    TfLiteType type = TfLiteTensorType(output);

    float *scores = malloc(sizeof(float)*num_classes);

    /* ------------------------------------------------ */
    /* read tensor (handle quantization)                */
    /* ------------------------------------------------ */

    if(type == kTfLiteFloat32)
    {
        TfLiteTensorCopyToBuffer(
            output,
            scores,
            sizeof(float)*num_classes);
    }

    else if(type == kTfLiteUInt8)
    {
        uint8_t *tmp = malloc(num_classes);

        TfLiteTensorCopyToBuffer(output,tmp,num_classes);

        TfLiteQuantizationParams q =
            TfLiteTensorQuantizationParams(output);

        for(int i=0;i<num_classes;i++)
            scores[i] = (tmp[i]-q.zero_point)*q.scale;

        free(tmp);
    }

    else if(type == kTfLiteInt8)
    {
        int8_t *tmp = malloc(num_classes);

        TfLiteTensorCopyToBuffer(output,tmp,num_classes);

        TfLiteQuantizationParams q =
            TfLiteTensorQuantizationParams(output);

        for(int i=0;i<num_classes;i++)
            scores[i] = (tmp[i]-q.zero_point)*q.scale;

        free(tmp);
    }

    else
    {
        printf("unsupported tensor type\n");
        return 1;
    }

    /* ------------------------------------------------ */
    /* find top-k predictions                           */
    /* ------------------------------------------------ */

    printf("\nTop %d predictions\n",TOPK);
    printf("------------------\n");

    for(int k=0;k<TOPK;k++)
    {
        int best = -1;
        float best_score = -1e9;

        for(int i=0;i<num_classes;i++)
        {
            if(scores[i] > best_score)
            {
                best_score = scores[i];
                best = i;
            }
        }

        scores[best] = -1e9;

        const char *label =
            (best < label_count) ?
            labels[best] : "unknown";

        /* IMPORTANT: use %s so label text is safe */

        printf("%d: %s (%.2f%%)\n",
               k+1,
               label,
               best_score*100.0f);
    }

    /* ------------------------------------------------ */
    /* cleanup                                          */
    /* ------------------------------------------------ */

    free(scores);
    free(resized);
    free(img);

    TfLiteInterpreterDelete(interpreter);
    TfLiteInterpreterOptionsDelete(options);
    TfLiteModelDelete(model);

    return 0;
}