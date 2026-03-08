/*
apt install libtensorflow-lite-dev => /usr/include/tensorflow/lite/c/c_api.h, /usr/lib/libtensorflow-lite.so
apt install libjpeg62-turbo-dev
gcc tflite_classify.c -o tflite_classify -ltensorflow-lite -ljpeg -lm -lpthread -ldl
./testmodel0 test/8.jpg model0/classify.tflite model0/bird_labels_de_latin.txt
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <tensorflow/lite/c/c_api.h>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#define MAX_LABELS 2048
#define MAX_LINE 512

char *labels[MAX_LABELS];
int label_count = 0;

void load_labels(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) {
        perror("labels");
        exit(1);
    }

    char line[MAX_LINE];

    while (fgets(line, sizeof(line), f)) {
        line[strcspn(line, "\n")] = 0;
        labels[label_count] = strdup(line);
        label_count++;
    }

    fclose(f);
}

int main(int argc, char **argv)
{
    if (argc < 4) {
        printf("Usage:\n");
        printf("%s image.jpg model.tflite labels.txt\n", argv[0]);
        return 1;
    }

    const char *image_path = argv[1];
    const char *model_path = argv[2];
    const char *labels_path = argv[3];

    load_labels(labels_path);

    /* load model */
    TfLiteModel *model = TfLiteModelCreateFromFile(model_path);

    TfLiteInterpreterOptions *options = TfLiteInterpreterOptionsCreate();
    TfLiteInterpreterOptionsSetNumThreads(options, 2);

    TfLiteInterpreter *interpreter =
        TfLiteInterpreterCreate(model, options);

    TfLiteInterpreterAllocateTensors(interpreter);

    /* input tensor */
    TfLiteTensor *input =
        TfLiteInterpreterGetInputTensor(interpreter, 0);

    int height = TfLiteTensorDim(input, 1);
    int width  = TfLiteTensorDim(input, 2);
    int channels = TfLiteTensorDim(input, 3);

    /* load image */
    int img_w, img_h, img_c;
    unsigned char *img = stbi_load(image_path, &img_w, &img_h, &img_c, 3);

    if (!img) {
        printf("Failed to load image\n");
        return 1;
    }

    /* simple resize (nearest neighbor) */
    unsigned char *resized = malloc(width * height * channels);

    for (int y=0; y<height; y++)
    for (int x=0; x<width; x++)
    {
        int srcx = x * img_w / width;
        int srcy = y * img_h / height;

        for (int c=0; c<3; c++)
            resized[(y*width+x)*3+c] =
                img[(srcy*img_w+srcx)*3+c];
    }

    /* copy input */
    TfLiteTensorCopyFromBuffer(
        input,
        resized,
        width * height * channels
    );

    /* run inference */
    if (TfLiteInterpreterInvoke(interpreter) != kTfLiteOk) {
        printf("invoke failed\n");
        return 1;
    }

    /* output tensor */
    const TfLiteTensor *output =
        TfLiteInterpreterGetOutputTensor(interpreter, 0);

    int num_classes = TfLiteTensorDim(output, 1);

    float *scores = malloc(sizeof(float)*num_classes);

    TfLiteTensorCopyToBuffer(
        output,
        scores,
        sizeof(float)*num_classes
    );

    int best = 0;
    float best_score = scores[0];

    for (int i=1;i<num_classes;i++) {
        if (scores[i] > best_score) {
            best_score = scores[i];
            best = i;
        }
    }

    printf("Number of classes: %d\n", num_classes);

    if (best < label_count)
        printf("Predicted class: %s (%.2f%%)\n",
               labels[best], best_score*100.0);
    else
        printf("Predicted class: %d (%.2f%%)\n",
               best, best_score*100.0);

    /* cleanup */
    free(scores);
    free(resized);
    stbi_image_free(img);

    TfLiteInterpreterDelete(interpreter);
    TfLiteInterpreterOptionsDelete(options);
    TfLiteModelDelete(model);

    return 0;
}